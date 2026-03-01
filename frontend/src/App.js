import React from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import './App.css';
import ContractList from './ContractList';
import ContractDetails from './ContractDetails';
import ContractAnalysis from './ContractAnalysis';

function Home() {
  const navigate = useNavigate();

  const handleOpenFolder = async () => {
    try {
      await fetch('http://localhost:8000/open-folder', { method: 'POST' });
    } catch (error) {
      console.error('Ошибка при открытии папки:', error);
      alert('Не удалось открыть папку.');
    }
  };

  return (
    <div className="home-container">
      <div className="header-actions">
        <div className="title-group">
          <h1>Каталог Договоров</h1>
          <p className="subtitle">Управление и интеллектуальный анализ документов</p>
        </div>
        <div className="button-group">
          <button onClick={() => navigate('/analysis')} className="analyze-nav-btn">
            🔍 Анализ новых договоров
          </button>
          <button onClick={handleOpenFolder} className="open-folder-btn">
            📂 Открыть хранилище
          </button>
        </div>
      </div>
      
      <ContractList />
    </div>
  );
}

function App() {
  return (
    <Router>
      <div className="App">
        <div className="App-header">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/analysis" element={<ContractAnalysis />} />
            <Route path="/contract/:id" element={<ContractDetails />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
