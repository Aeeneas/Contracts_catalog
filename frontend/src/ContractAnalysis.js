import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './App.css';

function ContractAnalysis() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadStatus, setUploadStatus] = useState('');
  const [analysisResults, setAnalysisResults] = useState([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (folderInputRef.current) {
      folderInputRef.current.setAttribute("webkitdirectory", "");
      folderInputRef.current.setAttribute("directory", "");
      folderInputRef.current.setAttribute("mozdirectory", "");
    }
  }, []);

  const handleFileChange = (event) => {
    if (event.target.files) {
      setSelectedFiles([...selectedFiles, ...Array.from(event.target.files)]);
    }
  };

  const handleFolderChange = (event) => {
    if (event.target.files) {
      const filteredFiles = Array.from(event.target.files).filter(file => {
        const ext = file.name.split('.').pop().toLowerCase();
        return ['pdf', 'docx', 'doc', 'xlsx', 'xls', 'zip'].includes(ext);
      });
      setSelectedFiles([...selectedFiles, ...filteredFiles]);
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
    const items = event.dataTransfer.items;
    if (!items) return;
    const files = [];
    const traverseFileTree = async (item, path = "") => {
      if (item.isFile) {
        const file = await new Promise((resolve) => item.file(resolve));
        const ext = file.name.split('.').pop().toLowerCase();
        if (['pdf', 'docx', 'doc', 'xlsx', 'xls', 'zip'].includes(ext)) { files.push(file); }
      } else if (item.isDirectory) {
        const dirReader = item.createReader();
        const entries = await new Promise((resolve) => { dirReader.readEntries(resolve); });
        for (const entry of entries) { await traverseFileTree(entry, path + item.name + "/"); }
      }
    };
    const promises = [];
    for (let i = 0; i < items.length; i++) {
      const entry = items[i].webkitGetAsEntry();
      if (entry) { promises.push(traverseFileTree(entry)); }
    }
    await Promise.all(promises);
    if (files.length > 0) { setSelectedFiles(prev => [...prev, ...files]); }
  };

  const handleRemoveFile = (indexToRemove) => {
    setSelectedFiles(selectedFiles.filter((_, index) => index !== indexToRemove));
  };

  const calculateMonthlyCost = (totalCost, startDate, endDate, workType) => {
    if (workType !== 'ТО' || !totalCost || !startDate || !endDate) return 0;
    const start = new Date(startDate);
    const end = new Date(endDate);
    if (isNaN(start) || isNaN(end) || end <= start) return 0;
    let months = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth());
    if (end.getDate() >= start.getDate() - 1) { months += 1; }
    return months > 0 ? Math.round((totalCost / months) * 100) / 100 : 0;
  };

  const handleAnalyze = async () => {
    if (selectedFiles.length === 0) {
      setUploadStatus('Пожалуйста, выберите файлы для загрузки.');
      return;
    }

    setUploadStatus('Анализ файлов...');
    setIsAnalyzing(true);
    let allResults = [];

    for (const file of selectedFiles) {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('http://localhost:8000/analyze', {
          method: 'POST',
          body: formData,
        });

        const data = await response.json();
        
        // Обработка либо одного файла, либо массива из ZIP
        const itemsToProcess = data.status === 'batch_analyzed' ? data.results : [data];

        itemsToProcess.forEach(item => {
          if (item.status === 'analyzed') {
            const aiData = item.extracted_data;
            const calculatedMonthly = aiData.work_type === 'ТО' 
              ? calculateMonthlyCost(aiData.contract_cost, aiData.start_date, aiData.end_date, aiData.work_type)
              : (aiData.monthly_cost || 0);

            allResults.push({
              id: Math.random().toString(36).substr(2, 9),
              temp_path: item.temp_path,
              filename: item.filename,
              file_hash: item.file_hash,
                              data: {
                                doc_type: aiData.doc_type || 'ДОГ',
                                company: aiData.company || '',
                                customer: aiData.customer || '',
                                                  customer_inn: aiData.customer_inn || '',
                                                  customer_ogrn: aiData.customer_ogrn || '',
                                                  customer_ceo: aiData.customer_ceo || '',
                                                  customer_legal_address: aiData.customer_legal_address || '',
                                                  customer_contacts: aiData.customer_contacts || '',
                                                  customer_bank_details: aiData.customer_bank_details || '',
                                
                                work_type: aiData.work_type || '',
                                work_address: aiData.work_address || '',
                                elevator_addresses: aiData.elevator_addresses || '',
                                contract_cost: aiData.contract_cost || 0,
                                monthly_cost: calculatedMonthly,
                                conclusion_date: aiData.conclusion_date || '',
                                start_date: aiData.start_date || '',
                                end_date: aiData.end_date || '',
                                                  stages_info: aiData.stages_info || 'Один этап',
                                                  short_description: item.summary || '',
                                                  ultra_short_summary: aiData.ultra_short_summary || ''
                                                },
                                              errors: {},
              status: 'analyzed'
            });
          } else if (item.status === 'duplicate_hash') {
            allResults.push({
              id: Math.random().toString(36).substr(2, 9),
              filename: item.filename,
              error: item.error,
              status: 'error',
              errorType: 'duplicate'
            });
          } else {
            allResults.push({
              id: Math.random().toString(36).substr(2, 9),
              filename: item.filename,
              error: item.error || item.details || 'Ошибка анализа',
              status: 'error',
              errorType: 'generic'
            });
          }
        });
      } catch (error) {
        console.error('Ошибка сети:', error);
      }
    }

    setAnalysisResults(prev => [...prev, ...allResults]);
    setUploadStatus(allResults.length > 0 ? 'Анализ завершен. Проверьте результаты.' : 'Не удалось проанализировать файлы.');
    setIsAnalyzing(false);
    setSelectedFiles([]);
  };

  const handleFieldChange = (id, field, value) => {
    setAnalysisResults(prev => prev.map(res => {
      if (res.id !== id) return res;
      const updatedData = { ...res.data, [field]: value };
      const updatedErrors = { ...res.errors, [field]: !value };
      if (['contract_cost', 'start_date', 'end_date', 'work_type'].includes(field)) {
        if (updatedData.work_type === 'ТО') {
          updatedData.monthly_cost = calculateMonthlyCost(updatedData.contract_cost, updatedData.start_date, updatedData.end_date, updatedData.work_type);
        }
      }
      return { ...res, data: updatedData, errors: updatedErrors };
    }));
  };

  const [activeError, setActiveError] = useState(null);

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    alert('Текст ошибки скопирован');
  };

  const handleFinalize = async (resultId) => {
    setActiveError(null);
    const resultToFinalize = analysisResults.find(r => r.id === resultId);
    if (!resultToFinalize) return;

    const mandatoryFields = ['company', 'customer', 'work_type'];
    const newErrors = {};
    let hasErrors = false;
    mandatoryFields.forEach(field => { if (!resultToFinalize.data[field]) { newErrors[field] = true; hasErrors = true; } });

    if (hasErrors) {
      setAnalysisResults(prev => prev.map(res => res.id === resultId ? { ...res, errors: newErrors } : res));
      setUploadStatus('Заполните обязательные поля.');
      return;
    }

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
          file_hash: resultToFinalize.file_hash,
          ...sanitizedData
        }),
      });

      const data = await response.json();
      if (response.ok) {
        setAnalysisResults(prev => prev.filter(r => r.id !== resultId));
        setUploadStatus(`Договор ${data.unique_number} сохранен!`);
      } else {
        const errorMsg = data.detail ? JSON.stringify(data.detail) : (data.message || data.error || 'Ошибка');
        setActiveError({ id: resultId, msg: errorMsg });
      }
    } catch (error) {
      setActiveError({ id: resultId, msg: `Ошибка сети: ${error.message}` });
    }
  };

  const handleCancel = async (resultId) => {
    const res = analysisResults.find(r => r.id === resultId);
    if (res && res.temp_path) {
      try { await fetch('http://localhost:8000/cancel-upload', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ temp_path: res.temp_path }) }); } catch (e) {}
    }
    setAnalysisResults(prev => prev.filter(r => r.id !== resultId));
  };

  return (
    <div className="analysis-page-container">
      <div className="analysis-header">
        <button onClick={() => navigate('/')} className="back-btn-styled">
          ← Вернуться к списку договоров
        </button>
        <h2>Анализ новых договоров</h2>
      </div>
      
      {!analysisResults.length && !selectedFiles.length && (
        <div className="centered-drop-container">
          <div className="drop-zone" onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop} onClick={() => fileInputRef.current.click()}>
            <div className="drop-zone-content">
              <span className="drop-icon">📁</span>
              <p>Перетащите <strong>файлы или папки</strong> сюда</p>
              <div className="drop-buttons">
                <button type="button" onClick={(e) => { e.stopPropagation(); fileInputRef.current.click(); }} className="drop-btn-action">Выбрать файлы</button>
                {/* <button type="button" onClick={(e) => { e.stopPropagation(); folderInputRef.current.click(); }} className="drop-btn-action">Выбрать папку</button> */}
              </div>
              <span className="drop-hint">PDF, Word, Excel, ZIP. Рекурсивное сканирование.</span>
            </div>
            <input type="file" multiple hidden ref={fileInputRef} onChange={handleFileChange} accept=".pdf,.docx,.doc,.xlsx,.xls,.zip" />
            <input type="file" hidden ref={folderInputRef} onChange={handleFolderChange} />
          </div>
        </div>
      )}

      {selectedFiles.length > 0 && (
        <div className="file-list-container">
          <h2>Выбранные файлы:</h2>
          <ul className="file-list">
            {selectedFiles.map((file, index) => (
              <li key={index}>{file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB) <button onClick={() => handleRemoveFile(index)} className="remove-file-btn">X</button></li>
            ))}
          </ul>
          <button onClick={handleAnalyze} className="upload-button" disabled={isAnalyzing}>{isAnalyzing ? 'Анализирую...' : 'Анализировать файлы'}</button>
        </div>
      )}

      {uploadStatus && <p className="upload-status">{uploadStatus}</p>}

      <div className="analysis-results">
        {analysisResults.map((result) => (
          <div key={result.id} className={`analysis-card ${result.status === 'error' ? 'card-error' : ''}`}>
            <h3>Файл: {result.filename}</h3>
            
            {result.status === 'error' ? (
              <div className="error-card-content">
                <p className="error-msg-main">{result.errorType === 'duplicate' ? '🚫 Дубликат обнаружен' : '⚠️ Ошибка анализа'}</p>
                <p className="error-msg-detail">{result.error}</p>
                <button onClick={() => handleCancel(result.id)} className="cancel-btn">Закрыть</button>
              </div>
            ) : (
              <>
                <div className="form-grid">
                  <label>Тип документа*:
                    <select value={result.data.doc_type} onChange={e => handleFieldChange(result.id, 'doc_type', e.target.value)}>
                      <option value="ДОГ">Договор</option><option value="ДС">Доп. соглашение</option><option value="АКТ">Акт</option><option value="КС-2">КС-2</option><option value="КС-3">КС-3</option>
                    </select>
                  </label>
                  <label className={result.errors?.company ? 'invalid-field' : ''}>Компания*:
                    <select value={result.data.company} onChange={e => handleFieldChange(result.id, 'company', e.target.value)}>
                      <option value="">Выберите компанию</option><option value="ТОР-ЛИФТ">ТОР-ЛИФТ</option><option value="Противовес">Противовес</option><option value="Противовес-Т">Противовес-Т</option>
                    </select>
                  </label>
                  <label className={result.errors?.customer ? 'invalid-field' : ''}>Заказчик*:
                    <input type="text" value={result.data.customer} onChange={e => handleFieldChange(result.id, 'customer', e.target.value)} />
                  </label>
                  <label>ИНН:
                    <input type="text" value={result.data.customer_inn} onChange={e => handleFieldChange(result.id, 'customer_inn', e.target.value)} />
                  </label>
                  <label>ОГРН:
                    <input type="text" value={result.data.customer_ogrn} onChange={e => handleFieldChange(result.id, 'customer_ogrn', e.target.value)} />
                  </label>
                  <label>Руководитель (Ген. директор):
                    <input type="text" value={result.data.customer_ceo} onChange={e => handleFieldChange(result.id, 'customer_ceo', e.target.value)} />
                  </label>
                  <label className="full-width">Юр. адрес:
                    <input type="text" value={result.data.customer_legal_address} onChange={e => handleFieldChange(result.id, 'customer_legal_address', e.target.value)} />
                  </label>
                  <label className="full-width">Контактные данные (Тел, Email):
                    <input type="text" value={result.data.customer_contacts} onChange={e => handleFieldChange(result.id, 'customer_contacts', e.target.value)} />
                  </label>
                  <label className="full-width">Банковские реквизиты:
                    <textarea value={result.data.customer_bank_details} onChange={e => handleFieldChange(result.id, 'customer_bank_details', e.target.value)} style={{height: '60px'}} />
                  </label>
                  <label className={result.errors?.work_type ? 'invalid-field' : ''}>Тип работ*:
                    <select value={result.data.work_type} onChange={e => handleFieldChange(result.id, 'work_type', e.target.value)}>
                      <option value="">Выберите тип</option><option value="ТО">ТО</option><option value="МОНТАЖ">МОНТАЖ</option><option value="СТРОЙКА">СТРОЙКА</option><option value="ПРОЕКТИРОВАНИЕ">ПРОЕКТИРОВАНИЕ</option><option value="КАПИТАЛЬНЫЕ РАБОТЫ">КАПИТАЛЬНЫЕ РАБОТЫ</option>
                    </select>
                  </label>
                  <label className="full-width">Адрес выполнения работ (Объект):
                    <input type="text" value={result.data.work_address} onChange={e => handleFieldChange(result.id, 'work_address', e.target.value)} />
                  </label>
                  <label className="full-width">Адреса лифтов:
                    <input type="text" value={result.data.elevator_addresses} onChange={e => handleFieldChange(result.id, 'elevator_addresses', e.target.value)} />
                  </label>
                  <label>Стоимость (общая):<input type="number" value={result.data.contract_cost} onChange={e => handleFieldChange(result.id, 'contract_cost', parseFloat(e.target.value))} /></label>
                  <label>Стоимость (месяц):<input type="number" value={result.data.monthly_cost} onChange={e => handleFieldChange(result.id, 'monthly_cost', parseFloat(e.target.value))} /></label>
                  <label>Дата заключения:<input type="date" value={result.data.conclusion_date} onChange={e => handleFieldChange(result.id, 'conclusion_date', e.target.value)} /></label>
                  <label>Дата начала:<input type="date" value={result.data.start_date} onChange={e => handleFieldChange(result.id, 'start_date', e.target.value)} /></label>
                  <label>Дата окончания:<input type="date" value={result.data.end_date} onChange={e => handleFieldChange(result.id, 'end_date', e.target.value)} /></label>
                                    <label className="full-width">Сверхкраткое описание (для таблицы):
                                      <input type="text" value={result.data.ultra_short_summary} onChange={e => handleFieldChange(result.id, 'ultra_short_summary', e.target.value)} placeholder='Напр: ТО 50 лифтов, Комсомольский проспект' />
                                    </label>
                                    <label className="full-width">Описание:
                  <textarea value={result.data.short_description} onChange={e => handleFieldChange(result.id, 'short_description', e.target.value)} /></label>
                </div>
                {activeError && activeError.id === result.id && (
                  <div className="error-block-inline">
                    <div className="error-content"><strong>Ошибка сохранения:</strong><pre>{activeError.msg}</pre></div>
                    <button onClick={() => copyToClipboard(activeError.msg)} className="copy-error-btn">📋 Копировать текст ошибки</button>
                  </div>
                )}
                <div className="card-actions">
                  <button onClick={() => handleFinalize(result.id)} className="confirm-btn">Подтвердить и Сохранить</button>
                  <button onClick={() => handleCancel(result.id)} className="cancel-btn">Отменить</button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default ContractAnalysis;
