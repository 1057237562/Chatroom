import os
import sys
import tempfile
from fastapi.testclient import TestClient
from main import app

def test_image_upload():
    client = TestClient(app)
    
    # Create a test image file
    test_image_content = b"fake image content for testing"
    
    # Test the upload endpoint
    response = client.post("/upload", files={"file": ("test.jpg", test_image_content, "image/jpeg")})
    
    print("Upload response:", response.json())
    
    # Test with invalid file type
    response = client.post("/upload", files={"file": ("test.txt", b"fake text", "text/plain")})
    print("Invalid file response:", response.json())
    
    # Test with no file
    response = client.post("/upload")
    print("No file response:", response.json())

if __name__ == "__main__":
    test_image_upload()