IT Inventory Management System
==============================

Overview
--------
Flask-based IT asset tracker with barcode tagging, backups, CSV import/export, and a desktop (pywebview + PyInstaller) build that runs without installing Python. Data stays portable in a `data/inventory.db` file next to the app.

Key Features
------------
- Assets: create/edit/delete, status workflow (In Stock, Assigned, Repair, Damaged, Missing, Disposed), movement history, vendor/location/category/subcategory linkage.
- Auto asset tags: configurable prefix; per-asset printable barcode; bulk printable barcode sheet (A4-friendly, compact CODE128).
- Categories & Sub-Categories: CRUD, CSV export/import, and backup.
- Locations, Vendors, Users: CRUD; vendor codes auto-generated (V001…).
- Statuses: In Stock, Assigned (default), Repair, Damaged, Missing, Disposed. Legacy `in_use` maps to Assigned.
- Settings: app name, support email, tag prefix, data backups (full DB), CSV export/import, data wipe (admin only), download links, barcode sheet link.
- Backups: one-click DB backup to `Data Backups`; restore with warning; CSVs can be saved to backups too.
- Dashboard: category pie, location bar, monthly movement line; sidebar collapse; theme toggle (light/dark).
- Portable data: SQLite DB at `data/inventory.db` next to the EXE (or override via `INVENTORY_DATA_DIR`).

Requirements (dev)
------------------
- Python 3.12+
- pip, virtualenv

Setup (source)
--------------
```bash
python -m venv venv
./venv/Scripts/activate   # Windows
pip install -r requirements.txt
flask db upgrade
python seed_data.py       # optional seed
python run_app.py         # http://127.0.0.1:5000
```
Default admin for fresh DBs: **admin / 123456**.

Desktop (windowed) build
------------------------
```bash
pip install pyinstaller pywebview
pyinstaller --noconfirm desktop_app.spec
```
Run `dist/ITInventory/ITInventory.exe`. Data lives in `data/inventory.db` beside the EXE. Copy the `data` folder to move/backup everything.

Data & Backups
--------------
- Primary DB: `data/inventory.db` (next to EXE or project root in dev). Override with `INVENTORY_DATA_DIR`.
- One-click DB backups saved to `Data Backups/` next to the app.
- Restore from Settings (warning: overwrites current data; a pre-restore copy is kept).
- CSV exports/imports for assets and categories/subcategories; in desktop mode you can also “Save CSV to Backups Folder”.

Barcodes & Printing
-------------------
- Per-asset label: `/assets/<id>/label` (compact barcode + tag + name; auto print).
- Bulk sheet: Settings → “Open Printable Asset Barcode Sheet” (A4-friendly grid of compact CODE128 tags; auto print).

Import/Export
-------------
- Assets CSV headers: `asset_tag, name, status, category_code, subcategory_name, location_code, vendor_name, serial_number, purchase_date, warranty_expiry_date, cost, description, notes`
- Categories/Sub-Categories CSV headers: `category_code, category_name, category_description, subcategory_name, subcategory_description`

Status Workflow
---------------
Active: In Stock, Assigned, Repair, Damaged, Missing, Disposed. Legacy `in_use` is treated as Assigned.

Portability
-----------
All data stays with `data/inventory.db` (or configured dir). For USB use, keep the EXE and `data` folder together; run the EXE from the stick.

Security
--------
- Change `SECRET_KEY` in production (env var or config).
- Default admin exists only on fresh DB; change the password after first login.

Screenshots
-----------
_(to be added)_

Acknowledgements
----------------
This project was built entirely with the assistance of Open AI's GPT-5.1-Codex-Max. The core logic, features, and final implementation were directed and completed by the project author.

License
-------
MIT License (see LICENSE)
