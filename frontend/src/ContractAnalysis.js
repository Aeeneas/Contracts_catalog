import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './App.css';
import './ContractAnalysis.css';

function ContractAnalysis() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [analysisResults, setAnalysisResults] = useState([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef(null);
  const consoleRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [logs]);

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

  const handleDrop = async (event) => {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');
    if (event.dataTransfer.files) {
      setSelectedFiles([...selectedFiles, ...Array.from(event.dataTransfer.files)]);
    }
  };

  const addLog = (msg, status = 'info') => {
    setLogs(prev => [...prev, { msg, status, time: new Date().toLocaleTimeString() }]);
  };

  const handleAnalyze = async () => {
    if (selectedFiles.length === 0) return;
    setIsAnalyzing(true);
    setLogs([]);
    setProgress(5);
    setAnalysisResults([]);
    const totalFiles = selectedFiles.length;
    let completedFiles = 0;

    for (const file of selectedFiles) {
      const formData = new FormData();
      formData.append('file', file);
      try {
        const response = await fetch('http://localhost:8000/analyze', { method: 'POST', body: formData });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop();
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const event = JSON.parse(line.replace('data: ', ''));
              if (event.log) addLog(event.log, event.status);
              if (event.final_result) {
                const res = event.final_result;
                if (res.status === 'analyzed') {
                  setAnalysisResults(prev => [...prev, {
                    id: Math.random().toString(36).substr(2, 9),
                    temp_path: res.temp_path, filename: res.filename, file_hash: res.file_hash, status: 'analyzed',
                    data: { ...res.extracted_data, short_description: res.summary || res.extracted_data.short_description || '' },
                    errors: {}
                  }]);
                } else {
                  setAnalysisResults(prev => [...prev, { id: Math.random().toString(36).substr(2, 9), filename: res.filename, error: res.error, status: 'error' }]);
                }
              }
            }
          }
        }
        completedFiles++;
        setProgress(Math.round((completedFiles / totalFiles) * 100));
      } catch (error) {
        addLog(`Ошибка: ${error.message}`, 'error');
      }
    }
    addLog('Обработка очереди завершена', 'success');
    setIsAnalyzing(false);
    setSelectedFiles([]);
  };

  const handleFieldChange = (id, field, value) => {
    setAnalysisResults(prev => prev.map(res => {
      if (res.id !== id) return res;
      return { ...res, data: { ...res.data, [field]: value } };
    }));
  };

  const handleFinalize = async (resultId) => {
    const result = analysisResults.find(r => r.id === resultId);
    if (!result) return;
    if (!result.data.company || !result.data.customer || !result.data.work_type) { alert('Заполните: Компания, Заказчик и Тип работ'); return; }
    
    const sanitizedData = {};
    Object.keys(result.data).forEach(key => {
      let val = result.data[key];
      if (val === '') val = null;
      if (['contract_cost', 'monthly_cost'].includes(key)) { val = val === null ? 0 : parseFloat(val); }
      if (key === 'elevator_count') { val = val === null ? 0 : parseInt(val); }
      sanitizedData[key] = val;
    });

    try {
      const response = await fetch('http://localhost:8000/finalize', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ temp_path: result.temp_path, filename: result.filename, file_hash: result.file_hash, ...sanitizedData }),
      });
      if (response.ok) {
        setAnalysisResults(prev => prev.filter(r => r.id !== resultId));
        addLog(`Файл сохранен: ${result.filename}`, 'success');
      } else {
        const err = await response.json();
        alert(`Ошибка валидации: ${JSON.stringify(err.detail)}`);
      }
    } catch (e) { addLog(`Ошибка: ${e.message}`, 'error'); }
  };

  const handleCancel = (id) => setAnalysisResults(prev => prev.filter(r => r.id !== id));

  return (
    <div className="analysis-page-container">
      <header className="home-header">
        <div className="header-left">
          <h1>Анализ документов</h1>
          <p className="subtitle">Интеллектуальная обработка файлов</p>
        </div>
      </header>

      {!isAnalyzing && !analysisResults.length && (
        <div className="centered-drop-container">
          <div className="drop-zone" onClick={() => fileInputRef.current.click()}>
            <p style={{fontSize: '1.2rem', fontWeight: 'bold'}}>Перетащите файлы сюда или нажмите для выбора</p>
            <button className="drop-btn-action" style={{marginTop: '15px'}}>Выбрать файлы</button>
            <input type="file" multiple hidden ref={fileInputRef} onChange={handleFileChange} />
          </div>
          {selectedFiles.length > 0 && (
            <div className="file-list-container" style={{marginTop: '20px'}}>
              <ul className="file-list">{selectedFiles.map((f, i) => <li key={i}>{f.name}</li>)}</ul>
              <button onClick={handleAnalyze} className="upload-button" style={{backgroundColor: '#3498db'}}>Начать анализ</button>
            </div>
          )}
        </div>
      )}

      {(isAnalyzing || logs.length > 0) && (
        <div style={{marginTop: '20px'}}>
          <div className="progress-container"><div className="progress-bar-fill" style={{ width: `${progress}%` }}></div></div>
          <div className="analysis-console" ref={consoleRef}>
            {logs.map((log, i) => (<div key={i} className={`console-line ${log.status}`}><span className="console-time">[{log.time}]</span> {log.msg}</div>))}
          </div>
        </div>
      )}

      <div className="analysis-results">
        {analysisResults.map((result) => (
          <div key={result.id} className="analysis-card" style={{borderLeft: '6px solid #2c3e50'}}>
            <div className="card-header-flex" style={{display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #eee', paddingBottom: '10px', marginBottom: '20px'}}>
                <h3 style={{margin: 0, fontWeight: 'bold'}}>Файл: {result.filename}</h3>
                <span className="badge-ai">Анализ завершен</span>
            </div>
            
            <div className="form-grid">
                <div className="form-group-title full-width">Основная информация</div>
                <label><strong>Тип документа</strong>
                  <select value={result.data.doc_type} onChange={e => handleFieldChange(result.id, 'doc_type', e.target.value)}>
                    <option value="ДОГ">Договор</option><option value="ДС">ДС</option><option value="АКТ">Акт</option><option value="КС-2">КС-2</option><option value="КС-3">КС-3</option>
                  </select>
                </label>
                <label><strong>Компания</strong>
                  <select value={result.data.company} onChange={e => handleFieldChange(result.id, 'company', e.target.value)}>
                    <option value="">Выберите...</option><option value="ТОР-ЛИФТ">ТОР-ЛИФТ</option><option value="Противовес">Противовес</option><option value="Противовес-Т">Противовес-Т</option>
                  </select>
                </label>
                <label><strong>Тип работ</strong>
                  <select value={result.data.work_type} onChange={e => handleFieldChange(result.id, 'work_type', e.target.value)}>
                    <option value="">Выберите...</option><option value="ТО">ТО</option><option value="МОНТАЖ">МОНТАЖ</option><option value="СТРОЙКА">СТРОЙКА</option><option value="ПРОЕКТИРОВАНИЕ">ПРОЕКТИРОВАНИЕ</option><option value="КАПИТАЛЬНЫЕ РАБОТЫ">КАПИТАЛЬНЫЕ РАБОТЫ</option>
                  </select>
                </label>

                <div className="form-group-title full-width">Данные заказчика</div>
                <label className="full-width"><strong>Заказчик</strong>
                  <input type="text" value={result.data.customer} onChange={e => handleFieldChange(result.id, 'customer', e.target.value)} />
                </label>
                <label><strong>ИНН</strong><input type="text" value={result.data.customer_inn} onChange={e => handleFieldChange(result.id, 'customer_inn', e.target.value)} /></label>
                <label><strong>ОГРН</strong><input type="text" value={result.data.customer_ogrn} onChange={e => handleFieldChange(result.id, 'customer_ogrn', e.target.value)} /></label>
                <label><strong>Директор</strong><input type="text" value={result.data.customer_ceo} onChange={e => handleFieldChange(result.id, 'customer_ceo', e.target.value)} /></label>
                <label className="full-width"><strong>Юридический адрес</strong><input type="text" value={result.data.customer_legal_address} onChange={e => handleFieldChange(result.id, 'customer_legal_address', e.target.value)} /></label>
                <label className="full-width"><strong>Реквизиты</strong><textarea value={result.data.customer_bank_details} onChange={e => handleFieldChange(result.id, 'customer_bank_details', e.target.value)} rows="2" /></label>

                <div className="form-group-title full-width">Сроки и стоимость</div>
                <label className="full-width"><strong>Адрес работ</strong><input type="text" value={result.data.work_address} onChange={e => handleFieldChange(result.id, 'work_address', e.target.value)} /></label>
                <label className="full-width"><strong>Адреса лифтов (через точку с запятой)</strong>
                  <textarea value={result.data.elevator_addresses} onChange={e => handleFieldChange(result.id, 'elevator_addresses', e.target.value)} rows="3" />
                </label>
                <label><strong>Общая сумма</strong><input type="number" value={result.data.contract_cost} onChange={e => handleFieldChange(result.id, 'contract_cost', parseFloat(e.target.value))} /></label>
                <label><strong>В месяц</strong><input type="number" value={result.data.monthly_cost} onChange={e => handleFieldChange(result.id, 'monthly_cost', parseFloat(e.target.value))} /></label>
                <label><strong>Количество лифтов</strong><input type="number" value={result.data.elevator_count} onChange={e => handleFieldChange(result.id, 'elevator_count', parseInt(e.target.value))} /></label>
                <label><strong>Дата заключения</strong><input type="date" value={result.data.conclusion_date} onChange={e => handleFieldChange(result.id, 'conclusion_date', e.target.value)} /></label>
                <label><strong>Начало</strong><input type="date" value={result.data.start_date} onChange={e => handleFieldChange(result.id, 'start_date', e.target.value)} /></label>
                <label><strong>Окончание</strong><input type="date" value={result.data.end_date} onChange={e => handleFieldChange(result.id, 'end_date', e.target.value)} /></label>

                <div className="form-group-title full-width">Резюме</div>
                <label className="full-width"><strong>Сводка</strong><input type="text" value={result.data.ultra_short_summary} onChange={e => handleFieldChange(result.id, 'ultra_short_summary', e.target.value)} /></label>
                <label className="full-width"><strong>Полное описание</strong><textarea value={result.data.short_description} onChange={e => handleFieldChange(result.id, 'short_description', e.target.value)} rows="12" style={{minHeight: '200px'}} /></label>
            </div>
            <div className="card-actions">
              <button onClick={() => handleFinalize(result.id)} className="confirm-btn">Сохранить в реестр</button>
              <button onClick={() => handleCancel(result.id)} className="cancel-btn">Удалить из очереди</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ContractAnalysis;
