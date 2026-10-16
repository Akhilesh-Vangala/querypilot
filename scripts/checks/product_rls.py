"""Run the actual migration and two-owner policies in a disposable PostgreSQL DB.

QUERY_PRODUCT_TEST_ADMIN_URL must point to a test PostgreSQL service with CREATE
DATABASE/ROLE privileges. This script creates/drops its own random database;
it never applies the migration to the supplied database or a hosted project.
"""
import concurrent.futures
import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb


def main():
    admin_url = os.environ["QUERY_PRODUCT_TEST_ADMIN_URL"]
    database = "querypilot_product_test_" + uuid4().hex[:12]
    owner, other = str(uuid4()), str(uuid4())
    passed = []
    with psycopg.connect(admin_url, autocommit=True) as admin:
        for role in ("anon", "authenticated"):
            if not admin.execute("select 1 from pg_roles where rolname=%s", [role]).fetchone():
                admin.execute(sql.SQL("create role {} nologin").format(sql.Identifier(role)))
        admin.execute(sql.SQL("create database {} encoding 'UTF8' template template0").format(sql.Identifier(database)))
        test_url = make_conninfo(admin_url, dbname=database)
        try:
            with psycopg.connect(test_url, autocommit=True) as root:
                root.execute("create schema auth; create table auth.users(id uuid primary key)")
                root.execute("create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$")
                root.execute("grant usage on schema auth to anon, authenticated; grant execute on function auth.uid() to anon, authenticated")
                root.execute("insert into auth.users values (%s),(%s)", [owner, other])
                root.execute((Path(__file__).resolve().parents[2]/"infrastructure/supabase/migrations/001_product_workspace.sql").read_text())

            def act(who, query, params=(), role="authenticated"):
                with psycopg.connect(test_url) as connection:
                    connection.execute(sql.SQL("set local role {}").format(sql.Identifier(role)))
                    connection.execute("select set_config('request.jwt.claim.sub', %s, true)", [who])
                    result = connection.execute(query, params)
                    return result.fetchall() if result.description else []

            def denied(who, query, params=(), role="authenticated"):
                try:
                    act(who, query, params, role)
                except psycopg.Error:
                    return
                raise AssertionError("An unauthorized write unexpectedly succeeded")

            project = str(uuid4())
            act(owner, "insert into querypilot_projects(id,owner_id,name) values (%s,%s,'Revenue')", [project, owner])
            assert act(owner, "select name from querypilot_projects") == [("Revenue",)]
            assert act(other, "select name from querypilot_projects") == []
            denied(owner, "select * from querypilot_projects", role="anon")
            denied(other, "insert into querypilot_projects(id,owner_id,name) values (%s,%s,'spoof')", [str(uuid4()), owner])
            denied(owner, "update querypilot_projects set name='overwrite'")
            passed.append("real-RLS-owner-visibility-anon-denial-spoofing-and-no-update")

            insert = "insert into querypilot_investigations(id,owner_id,project_id,title,filename,status,source_sha256,contract,profile) values (%s,%s,%s,'Revenue','own.csv','draft',%s,%s,%s)"
            values = [str(uuid4()), owner, project, "a"*64, Jsonb({}), Jsonb({})]
            act(owner, insert, values)
            denied(other, insert, [str(uuid4()), other, project, "b"*64, Jsonb({}), Jsonb({})])
            denied(owner, insert, values)
            assert act(other, "delete from querypilot_investigations returning id") == []
            denied(owner, "delete from querypilot_projects where id=%s", [project])
            passed.append("foreign-project-denied-immutable-ID-owner-delete-and-project-reference")

            def create_project(i):
                try:
                    act(owner, "insert into querypilot_projects(id,owner_id,name) values (%s,%s,%s)", [str(uuid4()), owner, "Project " + str(i)])
                    return True
                except psycopg.errors.CheckViolation:
                    return False
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                outcomes = list(pool.map(create_project, range(26)))
            assert sum(outcomes) == 19, outcomes
            assert act(owner, "select count(*) from querypilot_projects")[0][0] == 20
            passed.append("concurrent-project-inserts-enforce-exact-owner-quota")
            for _ in range(99):
                act(owner, insert, [str(uuid4()), owner, None, "c"*64, Jsonb({}), Jsonb({})])
            denied(owner, insert, [str(uuid4()), owner, None, "d"*64, Jsonb({}), Jsonb({})])
            assert act(owner, "select count(*) from querypilot_investigations")[0][0] == 100
            assert act(other, "select count(*) from querypilot_investigations")[0][0] == 0
            passed.append("per-owner-investigation-quota-and-complete-isolation")
            print(json.dumps({"passed": True, "checks": passed, "scope": "Actual local PostgreSQL policies; hosted Supabase Auth/email remain untested."}))
        finally:
            admin.execute(sql.SQL("drop database {} with (force)").format(sql.Identifier(database)))


if __name__ == "__main__":
    main()
