Campus Lost & Found System - how to run (Windows, VS Code)

1. Install Python (tick "Add Python to PATH").
2. Unzip this folder and open it in VS Code (File > Open Folder).
3. Open a terminal (Terminal > New Terminal) and run:
       pip install flask
4. Run the project:
       python app.py
5. Open http://127.0.0.1:5000 in your browser.

database.db is created automatically and items.csv / claims.csv are loaded
into it on start (no duplicates). To reload from scratch, stop the app,
delete database.db and run again.
