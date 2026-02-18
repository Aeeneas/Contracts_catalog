import React, { useState, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';
import ContractList from './ContractList';
import ContractDetails from './ContractDetails'; // Добавлен импорт ContractDetails

function Home() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadStatus, setUploadStatus] = useState('');
  const [responseDetails, setResponseDetails] = useState([]);
  const fileInputRef = useRef(null);

  const handleFileChange = (event) => {
    if (event.target.files) {
      setSelectedFiles([...selectedFiles, ...Array.from(event.target.files)]);
    }
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    event.currentTarget.classList.add('drag-over');
  };

  const handleDragLeave = (event) => {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');
  };

  const handleDrop = (event) => {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');
    if (event.dataTransfer.files) {
      setSelectedFiles([...selectedFiles, ...Array.from(event.dataTransfer.files)]);
    }
  };

  const handleRemoveFile = (indexToRemove) => {
    setSelectedFiles(selectedFiles.filter((_, index) => index !== indexToRemove));
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setUploadStatus('Пожалуйста, выберите файлы для загрузки.');
      return;
    }

    setUploadStatus('Загрузка...');
    setResponseDetails([]);

    const formData = new FormData();
    selectedFiles.forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      if (response.ok) {
        setUploadStatus('Загрузка завершена успешно!');
        setResponseDetails(data.details);
        setSelectedFiles([]); // Clear selected files after successful upload
      } else {
        setUploadStatus(`Ошибка загрузки: ${data.message || 'Неизвестная ошибка'}`);
        setResponseDetails(data.details || []);
      }
    } catch (error) {
      setUploadStatus(`Ошибка сети: ${error.message}`);
      console.error('Ошибка при загрузке файлов:', error);
    }
  };

  return (
    <div className="home-container">
      <h1>Портал Каталогизатора Договоров</h1>
      <div 
        className="drop-zone"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current.click()}
      >
        <p>Перетащите файлы сюда или нажмите, чтобы выбрать</p>
        <input
          type="file"
          multiple
          hidden
          ref={fileInputRef}
          onChange={handleFileChange}
        />
      </div>

      {selectedFiles.length > 0 && (
        <div className="file-list-container">
          <h2>Выбранные файлы:</h2>
          <ul className="file-list">
            {selectedFiles.map((file, index) => (
              <li key={index}>
                {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                <button onClick={() => handleRemoveFile(index)} className="remove-file-btn">X</button>
              </li>
            ))}
          </ul>
          <button onClick={handleUpload} className="upload-button">
            Загрузить все
          </button>
        </div>
      )}

      {uploadStatus && <p className="upload-status">{uploadStatus}</p>}

      {responseDetails.length > 0 && (
        <div className="response-details">
          <h2>Результаты обработки:</h2>
          <ul className="response-list">
            {responseDetails.map((detail, index) => (
              <li key={index} className={detail.status.includes('failed') ? 'status-failed' : 'status-success'}>
                <strong>{detail.filename}:</strong> {detail.status}
                {detail.error && <span className="error-message"> - {detail.error}</span>}
                {detail.extracted_data && <pre>{JSON.stringify(detail.extracted_data, null, 2)}</pre>}
              </li>
            ))}
          </ul>
        </div>
      )}
      <ContractList />
    </div>
  );
}

function App() {
  return (
    <Router>
      <div className="App">
        <header className="App-header">
          <nav className="main-nav">
            <Link to="/" className="nav-link">Главная (Загрузка & Список)</Link>
          </nav>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/contract/:id" element={<ContractDetails />} />
          </Routes>
        </header>
      </div>
    </Router>
  );
}

export default App;
