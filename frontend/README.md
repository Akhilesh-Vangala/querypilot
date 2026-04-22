# QueryPilot frontend

- [Application](src/app/): route composition.
- [Features](src/features/): auth, investigations, comparisons, catalog, evaluation, history and workbench screens.
- [Components](src/components/): shared charts, reports and layout.
- [Client](src/lib/): typed API calls; [styles](src/styles/) own shared presentation.
- [Recordings](public/recordings/): native video player and actual continuous capture.
- [Configuration](config/): Nginx routing.

Run `npm ci` and `npm run build` from this directory. [Full layout](../docs/development/LAYOUT.md).

- [Own-data product](src/features/product/): landing/workspace, guided contracts, exact analytical results, device projects/history, recovery and optional accounts. [Upload recordings](public/uploads/) retain the public media routes.
