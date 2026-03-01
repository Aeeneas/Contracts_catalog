import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './ContractDetails.css';

function ContractDetails() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [contract, setContract] = useState(null);
    const [customer, setCustomer] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isEditing, setIsEditing] = useState(false);
    const [editData, setEditData] = useState({});

    useEffect(() => {
        const fetchData = async () => {
            try {
                const resContract = await fetch(`http://localhost:8000/contracts/${id}`);
                if (!resContract.ok) throw new Error('Договор не найден');
                const dataContract = await resContract.json();
                setContract(dataContract);
                setEditData(dataContract);

                if (dataContract.customer_id) {
                    const resCustomer = await fetch(`http://localhost:8000/customers/${dataContract.customer_id}`);
                    if (resCustomer.ok) {
                        const dataCustomer = await resCustomer.json();
                        setCustomer(dataCustomer);
                    }
                }
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [id]);

    const handleEditToggle = () => {
        setIsEditing(!isEditing);
        if (!isEditing) setEditData(contract);
    };

    const handleFieldChange = (field, value) => {
        setEditData(prev => ({ ...prev, [field]: value }));
    };

    const handleSave = async () => {
        try {
            const sanitizedData = { ...editData };
            delete sanitizedData.id;
            delete sanitizedData.upload_date;
            delete sanitizedData.unique_contract_number;
            delete sanitizedData.catalog_path;
            delete sanitizedData.ai_analysis_status;
            delete sanitizedData.customer_id;

            const response = await fetch(`http://localhost:8000/contracts/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(sanitizedData),
            });

            if (!response.ok) throw new Error('Ошибка сохранения');
            const updated = await response.json();
            setContract(updated);
            setIsEditing(false);
            alert('Сохранено!');
        } catch (err) {
            alert(err.message);
        }
    };

    const handleDelete = async () => {
        if (!window.confirm('Удалить этот договор?')) return;
        try {
            const res = await fetch(`http://localhost:8000/contracts/${id}`, { method: 'DELETE' });
            if (res.ok) { alert('Удалено'); navigate('/'); }
        } catch (err) { alert(err.message); }
    };

    if (loading) return <p className="details-loading">Загрузка...</p>;
    if (error) return <p className="details-error">{error}</p>;
    if (!contract) return <p className="details-not-found">Не найдено.</p>;

    return (
        <div className="contract-details-container">
            {/* Шапка с кнопками */}
            <div className="details-header">
                <button onClick={() => navigate('/')} className="back-button">&larr; Назад к списку</button>
                <div className="header-buttons">
                    {!isEditing ? (
                        <><button onClick={handleEditToggle} className="edit-btn">✏️ Редактировать</button><button onClick={handleDelete} className="delete-btn">🗑️ Удалить</button></>
                    ) : (
                        <><button onClick={handleSave} className="save-btn">💾 Сохранить</button><button onClick={handleEditToggle} className="cancel-btn-small">Отмена</button></>
                    )}
                </div>
            </div>

            {/* ОСНОВНОЙ БЛОК: ТИП, ИСПОЛНИТЕЛЬ, СУММА */}
            <div className="highlights-bar">
                <div className="highlight-item">
                    <label>Тип документа</label>
                    {isEditing ? (
                        <select value={editData.doc_type} onChange={e => handleFieldChange('doc_type', e.target.value)}>
                            <option value="ДОГ">Договор</option><option value="ДС">Доп. соглашение</option><option value="АКТ">Акт</option><option value="КС-2">КС-2</option><option value="КС-3">КС-3</option>
                        </select>
                    ) : <strong>{contract.doc_type}</strong>}
                </div>
                <div className="highlight-item">
                    <label>Вид работ</label>
                    {isEditing ? (
                        <select value={editData.work_type} onChange={e => handleFieldChange('work_type', e.target.value)}>
                            <option value="ТО">ТО</option><option value="МОНТАЖ">МОНТАЖ</option><option value="СТРОЙКА">СТРОЙКА</option><option value="ПРОЕКТИРОВАНИЕ">ПРОЕКТИРОВАНИЕ</option><option value="КАПИТАЛЬНЫЕ РАБОТЫ">КАПИТАЛЬНЫЕ РАБОТЫ</option>
                        </select>
                    ) : <strong>{contract.work_type}</strong>}
                </div>
                <div className="highlight-item">
                    <label>Компания исполнитель</label>
                    <strong>{contract.company}</strong>
                </div>
                <div className="highlight-item">
                    <label>Общая сумма контракта</label>
                    {isEditing ? (
                        <input type="number" value={editData.contract_cost} onChange={e => handleFieldChange('contract_cost', parseFloat(e.target.value))} />
                    ) : <strong className="price-tag">{contract.contract_cost.toLocaleString()} ₽</strong>}
                </div>
                {contract.work_type === 'ТО' && (
                    <div className="highlight-item">
                        <label>В месяц</label>
                        <strong>{contract.monthly_cost?.toLocaleString()} ₽</strong>
                    </div>
                )}
            </div>

            <h2 className="contract-number-title">
                {contract.doc_type} № {contract.unique_contract_number} — {contract.work_type}
            </h2>
            
            <div className="content-layout">
                {/* Секция: Информация о работах */}
                <div className="details-section">
                    <h3 className="section-title">🛠️ Сведения о работах и сроки</h3>
                    <div className="details-grid-compact">
                        <div className="detail-item-inline"><strong>Вид работ:</strong> <span>{contract.work_type}</span></div>
                        <div className="detail-item-inline"><strong>Дата заключения:</strong> <span>{new Date(contract.conclusion_date).toLocaleDateString()}</span></div>
                        <div className="detail-item-inline"><strong>Срок выполнения с:</strong> <span>{new Date(contract.start_date).toLocaleDateString()}</span></div>
                        <div className="detail-item-inline"><strong>Срок выполнения по:</strong> <span>{new Date(contract.end_date).toLocaleDateString()}</span></div>
                        
                        <div className="detail-item-block"><strong>Объект (адрес работ):</strong> 
                            {isEditing ? <input type="text" value={editData.work_address || ''} onChange={e => handleFieldChange('work_address', e.target.value)} /> : <span>{contract.work_address || 'Адрес не указан'}</span>}
                        </div>
                        <div className="detail-item-block"><strong>Адреса лифтов на обслуживании:</strong> 
                            {isEditing ? <input type="text" value={editData.elevator_addresses || ''} onChange={e => handleFieldChange('elevator_addresses', e.target.value)} /> : <span className="small-text">{contract.elevator_addresses || 'Информация отсутствует'}</span>}
                        </div>
                        <div className="detail-item-block"><strong>Краткое содержание:</strong> 
                            {isEditing ? <textarea value={editData.short_description} onChange={e => handleFieldChange('short_description', e.target.value)} rows="4" /> : <p className="summary-text">{contract.short_description}</p>}
                        </div>
                    </div>
                </div>

                {/* Секция: Данные заказчика */}
                <div className="details-section">
                    <h3 className="section-title">🏢 Реквизиты заказчика</h3>
                    <div className="details-grid-compact">
                        <div className="detail-item-inline"><strong>Наименование:</strong> <span>{contract.customer}</span></div>
                        {customer ? (
                            <>
                                <div className="detail-item-inline"><strong>ИНН:</strong> <span>{customer.inn}</span></div>
                                <div className="detail-item-inline"><strong>ОГРН:</strong> <span>{customer.ogrn || '—'}</span></div>
                                <div className="detail-item-inline"><strong>Руководитель:</strong> <span>{customer.ceo_name || '—'}</span></div>
                                <div className="detail-item-block"><strong>Юридический адрес:</strong> <span>{customer.legal_address || '—'}</span></div>
                                <div className="detail-item-block"><strong>Контакты (тел/email):</strong> <span>{customer.contact_info || '—'}</span></div>
                                <div className="detail-item-block"><strong>Банковские реквизиты:</strong> <pre className="pre-wrap-small">{customer.bank_details || '—'}</pre></div>
                            </>
                        ) : (
                            <p className="no-data-hint">Реквизиты по ИНН не найдены.</p>
                        )}
                    </div>
                    
                    {!isEditing && (
                        <div className="system-info">
                            <p><strong>Путь к файлу:</strong> {contract.catalog_path}</p>
                            <p><strong>Дата загрузки в систему:</strong> {new Date(contract.upload_date).toLocaleString()}</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default ContractDetails;
