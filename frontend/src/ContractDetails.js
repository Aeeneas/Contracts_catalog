import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './ContractDetails.css';

function ContractDetails() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [contract, setContract] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isEditing, setIsEditing] = useState(false);
    const [editData, setEditData] = useState({});

    useEffect(() => {
        const fetchContractDetails = async () => {
            try {
                const response = await fetch(`http://localhost:8000/contracts/${id}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                setContract(data);
                setEditData(data); // Инициализируем данные для редактирования
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchContractDetails();
    }, [id]);

    const handleEditToggle = () => {
        setIsEditing(!isEditing);
        if (!isEditing) {
            setEditData(contract); // Сброс правок при входе в режим
        }
    };

    const handleFieldChange = (field, value) => {
        setEditData(prev => ({ ...prev, [field]: value }));
    };

    const handleSave = async () => {
        try {
            // Очистка данных перед отправкой
            const sanitizedData = { ...editData };
            delete sanitizedData.id;
            delete sanitizedData.upload_date;
            delete sanitizedData.unique_contract_number;
            delete sanitizedData.catalog_path;
            delete sanitizedData.ai_analysis_status;

            const response = await fetch(`http://localhost:8000/contracts/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(sanitizedData),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Не удалось сохранить изменения');
            }

            const updatedContract = await response.json();
            setContract(updatedContract);
            setIsEditing(false);
            alert('Изменения успешно сохранены!');
        } catch (err) {
            alert(`Ошибка при сохранении: ${err.message}`);
        }
    };

    const handleDelete = async () => {
        if (!window.confirm(`Вы уверены, что хотите БЕЗВОЗВРАТНО удалить договор ${contract.unique_contract_number} и его файл?`)) {
            return;
        }

        try {
            const response = await fetch(`http://localhost:8000/contracts/${id}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                throw new Error('Не удалось удалить договор');
            }

            alert('Договор успешно удален.');
            navigate('/'); // Перенаправляем на главную
        } catch (err) {
            alert(`Ошибка при удалении: ${err.message}`);
        }
    };

    if (loading) return <p className="details-loading">Загрузка деталей договора...</p>;
    if (error) return <p className="details-error">Ошибка при загрузке деталей: {error}</p>;
    if (!contract) return <p className="details-not-found">Договор не найден.</p>;

    return (
        <div className="contract-details-container">
            <div className="details-header">
                <button onClick={() => navigate('/')} className="back-button">
                    &larr; Назад к списку
                </button>
                <div className="header-buttons">
                    {!isEditing ? (
                        <>
                            <button onClick={handleEditToggle} className="edit-btn">✏️ Редактировать</button>
                            <button onClick={handleDelete} className="delete-btn">🗑️ Удалить</button>
                        </>
                    ) : (
                        <>
                            <button onClick={handleSave} className="save-btn">💾 Сохранить</button>
                            <button onClick={handleEditToggle} className="cancel-btn-small">Отмена</button>
                        </>
                    )}
                </div>
            </div>

            <h2>{isEditing ? 'Редактирование:' : 'Договор:'} {contract.unique_contract_number}</h2>
            
            <div className="details-grid">
                <div className="detail-item">
                    <strong>Тип документа:</strong> 
                    {isEditing ? (
                        <select value={editData.doc_type} onChange={e => handleFieldChange('doc_type', e.target.value)}>
                            <option value="ДОГ">Договор</option>
                            <option value="ДС">Доп. соглашение</option>
                            <option value="АКТ">Акт</option>
                            <option value="КС-2">КС-2</option>
                            <option value="КС-3">КС-3</option>
                        </select>
                    ) : <span>{contract.doc_type}</span>}
                </div>
                <div className="detail-item">
                    <strong>Компания:</strong> 
                    {isEditing ? (
                        <select value={editData.company} onChange={e => handleFieldChange('company', e.target.value)}>
                            <option value="ТОР-ЛИФТ">ТОР-ЛИФТ</option>
                            <option value="Противовес">Противовес</option>
                            <option value="Противовес-Т">Противовес-Т</option>
                        </select>
                    ) : <span>{contract.company}</span>}
                </div>
                <div className="detail-item">
                    <strong>Заказчик:</strong> 
                    {isEditing ? (
                        <input type="text" value={editData.customer} onChange={e => handleFieldChange('customer', e.target.value)} />
                    ) : <span>{contract.customer}</span>}
                </div>
                <div className="detail-item">
                    <strong>Тип работ:</strong> 
                    {isEditing ? (
                        <select value={editData.work_type} onChange={e => handleFieldChange('work_type', e.target.value)}>
                            <option value="ТО">ТО</option>
                            <option value="МОНТАЖ">МОНТАЖ</option>
                            <option value="СТРОЙКА">СТРОЙКА</option>
                            <option value="ПРОЕКТИРОВАНИЕ">ПРОЕКТИРОВАНИЕ</option>
                            <option value="КАПИТАЛЬНЫЕ РАБОТЫ">КАПИТАЛЬНЫЕ РАБОТЫ</option>
                        </select>
                    ) : <span>{contract.work_type}</span>}
                </div>
                <div className="detail-item">
                    <strong>Стоимость договора:</strong> 
                    {isEditing ? (
                        <input type="number" value={editData.contract_cost} onChange={e => handleFieldChange('contract_cost', parseFloat(e.target.value))} />
                    ) : <span>{contract.contract_cost.toLocaleString()} руб.</span>}
                </div>
                <div className="detail-item">
                    <strong>Стоимость в месяц:</strong> 
                    {isEditing ? (
                        <input type="number" value={editData.monthly_cost} onChange={e => handleFieldChange('monthly_cost', parseFloat(e.target.value))} />
                    ) : <span>{contract.monthly_cost ? `${contract.monthly_cost.toLocaleString()} руб.` : 'N/A'}</span>}
                </div>
                <div className="detail-item">
                    <strong>Дата заключения:</strong> 
                    {isEditing ? (
                        <input type="date" value={editData.conclusion_date} onChange={e => handleFieldChange('conclusion_date', e.target.value)} />
                    ) : <span>{new Date(contract.conclusion_date).toLocaleDateString()}</span>}
                </div>
                <div className="detail-item">
                    <strong>Дата начала:</strong> 
                    {isEditing ? (
                        <input type="date" value={editData.start_date} onChange={e => handleFieldChange('start_date', e.target.value)} />
                    ) : <span>{new Date(contract.start_date).toLocaleDateString()}</span>}
                </div>
                <div className="detail-item">
                    <strong>Дата окончания:</strong> 
                    {isEditing ? (
                        <input type="date" value={editData.end_date} onChange={e => handleFieldChange('end_date', e.target.value)} />
                    ) : <span>{new Date(contract.end_date).toLocaleDateString()}</span>}
                </div>
                <div className="detail-item full-width">
                    <strong>Краткое описание:</strong> 
                    {isEditing ? (
                        <textarea value={editData.short_description} onChange={e => handleFieldChange('short_description', e.target.value)} rows="5" />
                    ) : <span className="pre-wrap">{contract.short_description}</span>}
                </div>
                
                {!isEditing && (
                    <>
                        <div className="detail-item full-width">
                            <strong>Путь в каталоге:</strong> <span>{contract.catalog_path}</span>
                        </div>
                        <div className="detail-item">
                            <strong>Дата загрузки:</strong> <span>{new Date(contract.upload_date).toLocaleString()}</span>
                        </div>
                        <div className="detail-item">
                            <strong>Статус AI анализа:</strong> <span>{contract.ai_analysis_status}</span>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}

export default ContractDetails;
