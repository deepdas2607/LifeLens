# LifeLens Browser Extension

## Overview
The LifeLens browser extension allows patients to capture and save memories directly from their web browser. Selected text, images, and audio can be sent to the LifeLens system and stored in Qdrant for later retrieval.

## ⚠️ Important: API Server Required

**The extension REQUIRES the API server to be running** at `http://localhost:8000`

The extension works **INDEPENDENTLY of the Streamlit app** - you can close the Streamlit app and the extension will continue to function as long as the API server is running.

## Architecture

```
Browser Extension → FastAPI Server (port 8000) → Qdrant Database
                    ↑
Streamlit App (port 8501) - Optional, can be closed
```

## Installation

### 1. Install Dependencies

```bash
cd lifelens
pip install -r requirements.txt
```

### 2. Start the API Server

**Option A: API Server Only (for extension)**
```bash
# Run from project root
start_api_server.bat
```

**Option B: Both API and Streamlit**
```bash
# Run from project root
start_lifelens.bat
```

**Option C: Manual Start**
```bash
cd lifelens
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Load Extension in Browser

1. Open Chrome or Edge
2. Navigate to `chrome://extensions` (or `edge://extensions`)
3. Enable **Developer Mode** (toggle in top right)
4. Click **Load unpacked**
5. Select the `lifelens/extension` folder

## Features

### 1. Context Menu - Save Selected Text
- Select any text on a webpage
- Right-click and choose "Save selection to LifeLens"
- Text is automatically sent to Qdrant with:
  - Content
  - Page URL
  - Page title
  - Timestamp
  - Patient ID

### 2. Popup Interface
The extension popup provides:
- **Login**: Authenticate with patient credentials
- **Memory Lane**: View recent memories
- **Search**: Search your memories
- **Upload**: Upload images and audio files

### 3. Automatic Patient Detection
- If logged in as a patient, memories are saved to your account
- Caretakers can select which patient to save memories for

## Extension Files

- `manifest.json` - Extension configuration (Manifest V3)
- `background.js` - Service worker for context menu
- `popup.html` - Popup UI
- `popup.js` - Popup logic
- `styles.css` - Popup styles
- `memory-styles.css` - Memory display styles

## API Endpoints Used

### Authentication
- `POST /api/auth/login` - Login and get JWT token

### Memory Operations
- `POST /api/memory/create` - Create text memory
- `POST /api/upload/image` - Upload image memory
- `POST /api/upload/audio` - Upload audio memory
- `POST /api/search` - Search memories
- `GET /api/memories/{patient_id}` - Get recent memories

## Data Flow

1. **User Action**: User selects text or uploads file
2. **Extension**: Sends data to API with JWT token
3. **API Server**: Validates token and calls `upsert_memory()`
4. **upsert_memory()**: 
   - Generates embedding using Gemini
   - Stores in Qdrant `lifelens_collection`
   - Also stores mood events in `mood_events` collection if applicable
5. **Success**: Badge shows "OK" for 2 seconds

## Troubleshooting

### Extension shows "ERR" badge
- **Cause**: API server is not running
- **Solution**: Run `start_api_server.bat`

### Cannot load extension
- **Cause**: Extension folder path is incorrect
- **Solution**: Make sure to select `lifelens/extension` folder

### Login fails
- **Cause**: Wrong credentials or API server not running
- **Solution**: 
  - Verify API server is running at http://localhost:8000
  - Use correct patient credentials
  - Only patient accounts can use the extension

### Features not working
- Check browser console (F12) for errors
- Verify API server logs for issues
- Ensure Qdrant is running and accessible

## Security Notes

1. **JWT Authentication**: All requests require a valid JWT token
2. **CORS**: API allows all origins in dev mode (should restrict in production)
3. **Patient-Only**: Extension is restricted to patient accounts
4. **Token Storage**: Tokens stored in `chrome.storage.local` (secure)
5. **7-Day Expiry**: JWT tokens expire after 7 days

## Development

### Reload Extension
After making changes:
1. Go to `chrome://extensions`
2. Click the refresh icon on the LifeLens extension
3. Or disable and re-enable the extension

### View Logs
- **Extension Logs**: Right-click extension icon → Inspect popup
- **Service Worker Logs**: chrome://extensions → Service Worker → Inspect
- **API Logs**: Check terminal running API server

### Testing
1. Start API server
2. Load extension
3. Login with patient credentials
4. Try saving selected text from any webpage
5. Verify data appears in Qdrant

## API Server vs Streamlit App

| Component | Port | Purpose | Required for Extension? |
|-----------|------|---------|------------------------|
| API Server | 8000 | Handle extension requests | ✅ **YES** |
| Streamlit App | 8501 | Web UI for patients/caretakers | ❌ No |
| Qdrant | 6333 | Vector database | ✅ **YES** |

**Key Point**: You can close the Streamlit app and the extension will continue to work as long as:
- API server is running (port 8000)
- Qdrant database is running (port 6333)

## Default Credentials

For testing purposes, these accounts are available:

**Patient Accounts** (can use extension):
- Username: `patient1` / Password: `patient123`
- Username: `dd26` / Password: (custom password)
- Username: `test_patient` / Password: (custom password)

**Caretaker Accounts** (cannot use extension):
- Username: `caretaker1` / Password: `care123`

**Family Accounts** (cannot use extension):
- Username: `family1` / Password: `family123`

## Next Steps

1. ✅ Start API server: `start_api_server.bat`
2. ✅ Load extension in browser
3. ✅ Login with patient account (patient1 / patient123)
4. ✅ Start saving memories!
5. ❌ Close Streamlit if desired (extension still works!)

## Support

For issues or questions:
1. Check API server is running: http://localhost:8000
2. Check API endpoint: http://localhost:8000/
3. Review browser console logs (F12)
4. Review API server terminal logs
