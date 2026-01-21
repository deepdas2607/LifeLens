import os

def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def save_uploaded_file(uploaded_file, directory="temp"):
    """
    Saves an uploaded file to a temporary directory.
    """
    ensure_directory(directory)
    file_path = os.path.join(directory, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path
