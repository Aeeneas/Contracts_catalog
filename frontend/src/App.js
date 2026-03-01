import React, { useState, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';
import ContractList from './ContractList';
import ContractDetails from './ContractDetails'; // Добавлен импорт ContractDetails

function Home() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadStatus, setUploadStatus] = useState('');
  const [analysisResults, setAnalysisResults] = useState([]); // Список результатов анализа для подтверждения
  const [isAnalyzing, setIsAnalyzing] = useState(false);
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

  const handleAnalyze = async () => {
    if (selectedFiles.length === 0) {
      setUploadStatus('Пожалуйста, выберите файлы для загрузки.');
      return;
    }

    setUploadStatus('Анализ файлов...');
    setIsAnalyzing(true);
    const results = [];

    for (const file of selectedFiles) {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('http://localhost:8000/analyze', {
          method: 'POST',
          body: formData,
        });

        const data = await response.json();
                if (response.ok) {
                  const aiData = data.extracted_data;
                  const calculatedMonthly = aiData.work_type === 'ТО' 
                    ? calculateMonthlyCost(aiData.contract_cost, aiData.start_date, aiData.end_date, aiData.work_type)
                    : (aiData.monthly_cost || 0);
        
                  results.push({
                    id: Math.random().toString(36).substr(2, 9),
                    temp_path: data.temp_path,
                    filename: data.filename,
                    data: {
                      company: aiData.company || '',
                      customer: aiData.customer || '',
                      work_type: aiData.work_type || '',
                      contract_cost: aiData.contract_cost || 0,
                      monthly_cost: calculatedMonthly,
                      conclusion_date: aiData.conclusion_date || '',
                      start_date: aiData.start_date || '',
                      end_date: aiData.end_date || '',
                      stages_info: aiData.stages_info || 'Один этап',
                      short_description: data.summary || ''
                    },
                    status: 'analyzed'
                  });
                }
         else {
          console.error(`Ошибка анализа файла ${file.name}:`, data.error);
        }
      } catch (error) {
        console.error('Ошибка сети при анализе:', error);
      }
    }

    setAnalysisResults(results);
    setUploadStatus(results.length > 0 ? 'Анализ завершен. Пожалуйста, подтвердите данные.' : 'Не удалось проанализировать файлы.');
    setIsAnalyzing(false);
    setSelectedFiles([]);
  };

  const calculateMonthlyCost = (totalCost, startDate, endDate, workType) => {
    if (workType !== 'ТО' || !totalCost || !startDate || !endDate) return 0;
    
    const start = new Date(startDate);
    const end = new Date(endDate);
    
    if (isNaN(start) || isNaN(end) || end <= start) return 0;
    
    // Считаем разницу в месяцах
    let months = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth());
    
    // Если день окончания больше или равен дню начала, считаем текущий месяц полным
    if (end.getDate() >= start.getDate() - 1) {
      months += 1;
    }
    
    return months > 0 ? Math.round((totalCost / months) * 100) / 100 : 0;
  };

  const handleFieldChange = (id, field, value) => {
    setAnalysisResults(prev => prev.map(res => {
      if (res.id !== id) return res;
      
      const updatedData = { ...res.data, [field]: value };
      const updatedErrors = { ...res.errors, [field]: !value };

      // Если изменилось поле, влияющее на расчет ежемесячной стоимости ТО
      if (['contract_cost', 'start_date', 'end_date', 'work_type'].includes(field)) {
        if (updatedData.work_type === 'ТО') {
          updatedData.monthly_cost = calculateMonthlyCost(
            updatedData.contract_cost,
            updatedData.start_date,
            updatedData.end_date,
            updatedData.work_type
          );
        }
      }

      return { 
        ...res, 
        data: updatedData,
        errors: updatedErrors
      };
    }));
  };

  const handleFinalize = async (resultId) => {
    const resultToFinalize = analysisResults.find(r => r.id === resultId);
    if (!resultToFinalize) return;

    // Валидация обязательных полей
    const mandatoryFields = ['company', 'customer', 'work_type'];
    const newErrors = {};
    let hasErrors = false;

    mandatoryFields.forEach(field => {
      if (!resultToFinalize.data[field]) {
        newErrors[field] = true;
        hasErrors = true;
      }
    });

    if (hasErrors) {
      setAnalysisResults(prev => prev.map(res => 
        res.id === resultId ? { ...res, errors: newErrors } : res
      ));
      setUploadStatus('Пожалуйста, заполните обязательные поля (подсвечены красным).');
      return;
    }

    // Очистка данных перед отправкой (пустые строки -> null)
    const sanitizedData = {};
    Object.keys(resultToFinalize.data).forEach(key => {
      const val = resultToFinalize.data[key];
      sanitizedData[key] = val === '' ? null : val;
    });

    try {
      const response = await fetch('http://localhost:8000/finalize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          temp_path: resultToFinalize.temp_path,
          filename: resultToFinalize.filename,
          ...sanitizedData
        }),
      });

      const data = await response.json();
      if (response.ok) {
        setAnalysisResults(prev => prev.filter(r => r.id !== resultId));
        setUploadStatus(`Договор ${data.unique_number} успешно сохранен!`);
      } else {
        // Улучшенная обработка ошибок
        let errorMsg = 'Неизвестная ошибка';
        if (data.detail) {
          errorMsg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        } else if (data.message) {
          errorMsg = data.message;
        } else if (data.error) {
          errorMsg = data.error;
        }
        console.error('Ошибка сервера:', data);
        alert(`Ошибка при сохранении: ${errorMsg}`);
      }
    } catch (error) {
      console.error('Ошибка при завершении загрузки:', error);
      alert('Ошибка сети при сохранении. Проверьте консоль браузера.');
    }
  };

  const handleCancel = async (resultId) => {
    const resultToCancel = analysisResults.find(r => r.id === resultId);
    if (!resultToCancel) return;

    try {
      await fetch('http://localhost:8000/cancel-upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ temp_path: resultToCancel.temp_path }),
      });
    } catch (error) {
      console.error('Ошибка при удалении временного файла:', error);
    }

    setAnalysisResults(prev => prev.filter(r => r.id !== resultId));
    if (analysisResults.length === 1) {
      setUploadStatus('');
    }
  };

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
        <h1>Портал Каталогизатора Договоров</h1>
        <button onClick={handleOpenFolder} className="open-folder-btn">
          📂 Открыть папку с договорами
        </button>
      </div>
      
      {!analysisResults.length && (
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
            accept=".pdf,.docx,.doc,.xlsx,.xls,.zip"
          />
        </div>
      )}

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
          <button onClick={handleAnalyze} className="upload-button" disabled={isAnalyzing}>
            {isAnalyzing ? 'Анализирую...' : 'Анализировать файлы'}
          </button>
        </div>
      )}

      {uploadStatus && <p className="upload-status">{uploadStatus}</p>}

      {analysisResults.length > 0 && (
        <div className="analysis-results">
          <h2>Подтверждение данных:</h2>
          {analysisResults.map((result) => (
            <div key={result.id} className="analysis-card">
              <h3>Файл: {result.filename}</h3>
              <div className="form-grid">
                <label className={result.errors?.company ? 'invalid-field' : ''}>Компания*:
                  <select value={result.data.company} onChange={e => handleFieldChange(result.id, 'company', e.target.value)}>
                    <option value="">Выберите компанию</option>
                    <option value="ТОР-ЛИФТ">ТОР-ЛИФТ</option>
                    <option value="Противовес">Противовес</option>
                    <option value="Противовес-Т">Противовес-Т</option>
                  </select>
                </label>
                <label className={result.errors?.customer ? 'invalid-field' : ''}>Заказчик*:
                  <input type="text" value={result.data.customer} onChange={e => handleFieldChange(result.id, 'customer', e.target.value)} />
                </label>
                <label className={result.errors?.work_type ? 'invalid-field' : ''}>Тип работ*:
                  <select value={result.data.work_type} onChange={e => handleFieldChange(result.id, 'work_type', e.target.value)}>
                    <option value="">Выберите тип</option>
                    <option value="ТО">ТО</option>
                    <option value="МОНТАЖ">МОНТАЖ</option>
                    <option value="СТРОЙКА">СТРОЙКА</option>
                    <option value="ПРОЕКТИРОВАНИЕ">ПРОЕКТИРОВАНИЕ</option>
                    <option value="КАПИТАЛЬНЫЕ РАБОТЫ">КАПИТАЛЬНЫЕ РАБОТЫ</option>
                  </select>
                </label>
                <label>Стоимость (общая):
                  <input type="number" value={result.data.contract_cost} onChange={e => handleFieldChange(result.id, 'contract_cost', parseFloat(e.target.value))} />
                </label>
                <label>Стоимость (месяц):
                  <input type="number" value={result.data.monthly_cost} onChange={e => handleFieldChange(result.id, 'monthly_cost', parseFloat(e.target.value))} />
                </label>
                <label>Дата заключения:
                  <input type="date" value={result.data.conclusion_date} onChange={e => handleFieldChange(result.id, 'conclusion_date', e.target.value)} />
                </label>
                <label>Дата начала:
                  <input type="date" value={result.data.start_date} onChange={e => handleFieldChange(result.id, 'start_date', e.target.value)} />
                </label>
                <label>Дата окончания:
                  <input type="date" value={result.data.end_date} onChange={e => handleFieldChange(result.id, 'end_date', e.target.value)} />
                </label>
                <label className="full-width">Описание:
                  <textarea value={result.data.short_description} onChange={e => handleFieldChange(result.id, 'short_description', e.target.value)} />
                </label>
              </div>
              <div className="card-actions">
                <button onClick={() => handleFinalize(result.id)} className="confirm-btn">Подтвердить и Сохранить</button>
                <button onClick={() => handleCancel(result.id)} className="cancel-btn">Отменить</button>
              </div>
            </div>
          ))}
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
