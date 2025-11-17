import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";
const AUTH_HEADER = {
  Authorization: "Fake 11111111-2222-3333-4444-555555555555",
};

export default function CloudBox() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [status, setStatus] = useState("");

  // -----------------------
  // Fetch all saved files
  // -----------------------
  const fetchFiles = async () => {
    try {
      const res = await axios.get(`${API_BASE}/files/list?folder_id=null`, {
        headers: AUTH_HEADER,
      });

      setFiles(res.data.files || []);
    } catch (err) {
      console.error("Failed to fetch files:", err);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  // -----------------------
  // Upload file via S3 presigned URL
  // -----------------------
  const uploadFile = async () => {
    if (!selectedFile) return;

    setStatus("Uploading...");

    try {
      const presignRes = await axios.post(
        `${API_BASE}/files/presign-upload`,
        {
          file_name: selectedFile.name,
          mime_type: selectedFile.type,
          size_bytes: selectedFile.size,
          folder_id: null,
        },
        { headers: AUTH_HEADER }
      );

      // Upload to S3
      await axios.put(presignRes.data.upload_url, selectedFile, {
        headers: { "Content-Type": selectedFile.type },
      });

      setStatus("Upload successful ✔");
      setSelectedFile(null);

      fetchFiles();
      setTimeout(() => setStatus(""), 2000);
    } catch (err) {
      console.error("Upload failed:", err);
      setStatus("Upload failed ❌");
    }
  };

  // -----------------------
  // Download file
  // -----------------------
  const downloadFile = async (file_id) => {
    try {
      const res = await axios.get(
        `${API_BASE}/files/${file_id}/download-url`,
        { headers: AUTH_HEADER }
      );

      window.open(res.data.download_url, "_blank");
    } catch (err) {
      console.error("Download failed:", err);
      alert("Download failed ❌");
    }
  };

  // -----------------------
  // Delete file
  // -----------------------
  const deleteFile = async (file_id) => {
    try {
      await axios.delete(`${API_BASE}/files/${file_id}`, {
        headers: AUTH_HEADER,
      });

      fetchFiles();
    } catch (err) {
      console.error("Delete failed:", err);
      alert("Delete failed ❌");
    }
  };

  return (
    <div className="p-10 max-w-xl mx-auto text-white bg-black min-h-screen">
      <h1 className="text-3xl font-bold mb-6 text-center">My CloudBox</h1>

      {/* Select File */}
      <input
        type="file"
        onChange={(e) => setSelectedFile(e.target.files[0])}
        className="mb-4"
      />

      {/* Upload Button */}
      <button
        onClick={uploadFile}
        disabled={!selectedFile}
        className="bg-white text-black px-4 py-2 rounded"
      >
        Upload
      </button>

      {/* Status */}
      {status && <p className="mt-3 text-center">{status}</p>}

      {/* File List */}
      <div className="mt-8">
        {files.length === 0 && <p>No files uploaded yet</p>}

        {files.map((f) => (
          <div
            key={f.file_id}
            className="flex justify-between items-center p-3 border border-gray-600 rounded mb-2 bg-gray-900"
          >
            <span>{f.file_name}</span>

            <div className="space-x-3">
              <button
                onClick={() => downloadFile(f.file_id)}
                className="text-blue-400 hover:underline"
              >
                Download
              </button>

              <button
                onClick={() => deleteFile(f.file_id)}
                className="text-red-400 hover:underline"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

