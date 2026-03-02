import React from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, NavLink } from 'react-router-dom';
import './App.css';
import ContractList from './ContractList';
import ContractDetails from './ContractDetails';
import ContractAnalysis from './ContractAnalysis';
import CustomerList from './CustomerList';
import CustomerDetails from './CustomerDetails';

function Navigation() {
  const navigate = useNavigate();
  return (
    <nav className="main-nav">
      <div className="nav-container">
        <div className="nav-logo" onClick={() => navigate('/')}>
          Каталогизатор
        </div>
        <div className="nav-links">
          <NavLink to="/" className={({ isActive }) => "nav-link" + (isActive ? " active" : "")} end>Договоры</NavLink>
          <NavLink to="/customers" className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}>Заказчики</NavLink>
          <NavLink to="/analysis" className={({ isActive }) => "nav-link highlight" + (isActive ? " active" : "")}>Анализ</NavLink>
        </div>
      </div>
    </nav>
  );
}

function Home() {
  const handleOpenFolder = async () => {
    try {
      await fetch('http://localhost:8000/open-folder', { method: 'POST' });
    } catch (error) {
      console.error('Ошибка при открытии папки:', error);
      alert('Не удалось открыть папку.');
    }
  };

  return (
    <div className="page-container">
      <header className="home-header">
        <div className="header-left">
          <h1>Реестр договоров</h1>
          <p className="subtitle">Интеллектуальная система управления документами</p>
        </div>
        <div className="header-right">
          <button onClick={handleOpenFolder} className="open-folder-btn">
            Открыть хранилище
          </button>
        </div>
      </header>
      
      <div className="main-content-area">
        <ContractList />
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <div className="App">
        <Navigation />
        <main className="App-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/analysis" element={<div className="page-container"><ContractAnalysis /></div>} />
            <Route path="/customers" element={<div className="page-container"><CustomerWrapper /></div>} />
            <Route path="/customer/:id" element={<div className="page-container"><CustomerDetails /></div>} />
            <Route path="/contract/:id" element={<div className="page-container"><ContractDetails /></div>} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

function CustomerWrapper() {
  const navigate = useNavigate();
  return <CustomerList onSelectCustomer={(id) => navigate(`/customer/${id}`)} />;
}

export default App;
