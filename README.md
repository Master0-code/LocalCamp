# ⚙️ Setup

Follow these steps to run **Local Camp** on your computer.

## 1. Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/Local-Camp.git
cd Local-Camp
```

## 2. Create a Virtual Environment

It is recommended to use a virtual environment for Local Camp.

### Windows

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

## 3. Install Requirements

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## 4. Create the `.env` File

Create a file named:

```text
.env
```

in the same folder as `app.py`.

Add:

```env
SECRET_KEY=replace-with-a-long-random-string
APP_PASSWORD=anypasswordyouwant
```

### Important

Change both values before running Local Camp.

For example:

```env
SECRET_KEY=your-long-random-secret-key
APP_PASSWORD=your-local-camp-password
```

**Do not upload `.env` to GitHub.**

Make sure `.env` is included in your `.gitignore`:

```gitignore
.env
```

## 5. Set Your Library Folder

Open `app.py` and find the library folder setting.

Change it to the folder containing your Local Camp library:

```python
LIBRARY_FOLDER = r"C:\Path\To\Your\LocalLibrary"
```

Your library should contain the supported folders:

```text
LocalLibrary/
├── Pictures/
├── Music/
├── Videos/
└── Documents/
```

You can put your own files and subfolders inside these directories.

## 6. Start Local Camp

Run:

```bash
python app.py
```

If everything is configured correctly, Local Camp will start on your computer.

Open a browser and go to:

```text
http://localhost
```

## 7. Access Local Camp From Another Device

Make sure the other device is connected to the **same local network** as the computer running Local Camp.

Find the computer's local IP address:

```cmd
ipconfig
```

Look for the **IPv4 Address**.

For example:

```text
IPv4 Address . . . . . . : 192.168.1.10
```

Then open this address on another device:

```text
http://192.168.1.10
```

You can then access Local Camp from devices connected to the same LAN.

## 🔐 Security Notes

Local Camp is designed primarily for **private/local network use**.

* Keep your `.env` file private.
* Never publish your `SECRET_KEY`.
* Never publish your `APP_PASSWORD`.
* Do not put your personal Pictures, Music, Videos, or Documents inside the GitHub repository.
* Do not expose Local Camp directly to the public internet unless you understand and properly configure the required security measures.

## 🛑 Stopping Local Camp

Press:

```text
Ctrl + C
```

in the terminal running Local Camp.
