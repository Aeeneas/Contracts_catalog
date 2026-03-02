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
                    if (resCustomer.ok) setCustomer(await resCustomer.json());
                }
            } catch (err) { setError(err.message); } finally { setLoading(false); }
        };
        fetchData();
    }, [id]);

    const handleSave = async () => {
        try {
            const response = await fetch(`http://localhost:8000/contracts/${id}`, {
                method: 'PUT', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(editData),
            });
            if (response.ok) { 
                const updated = await response.json();
                setContract(updated); 
                setIsEditing(false); 
                alert('Данные договора успешно обновлены'); 
            }
        } catch (err) { alert(err.message); }
    };

    const handleOpenFolder = async () => {
        try { await fetch(`http://localhost:8000/contracts/${id}/open-folder`, { method: 'POST' }); } catch (err) { alert('Ошибка'); }
    };

    const handleDelete = async () => {
        if (!window.confirm('Удалить этот договор?')) return;
        try { const res = await fetch(`http://localhost:8000/contracts/${id}`, { method: 'DELETE' }); if (res.ok) navigate('/'); } catch (err) { alert(err.message); }
    };

    const getStatusInfo = (endDateStr) => {
        if (!endDateStr) return { label: 'Неопределено', class: 'status-undefined' };
        const today = new Date(); today.setHours(0,0,0,0);
        const endDate = new Date(endDateStr);
        if (isNaN(endDate.getTime())) return { label: 'Неопределено', class: 'status-undefined' };
        return today <= endDate ? { label: 'Действует', class: 'status-active' } : { label: 'Завершен', class: 'status-ended' };
    };

    if (loading) return <div className="p-10 center-text">Загрузка...</div>;
    if (error) return <div className="p-10 text-red-500 center-text">{error}</div>;

    const elevatorList = contract.elevator_addresses ? contract.elevator_addresses.split(/[;\n]/).map(s => s.trim()).filter(s => s.length > 0) : [];
    const status = getStatusInfo(contract.end_date);

    return (
        <div className="page-container">
            <header className="home-header">
                <div className="header-left">
                    <button onClick={() => navigate('/')} style={{background: 'none', color: '#3498db', padding: 0, marginBottom: '10px', fontWeight: 'bold'}}>← Назад</button>
                    <h1 style={{fontWeight: '900', textTransform: 'uppercase'}}>{contract.work_type} — {contract.customer}</h1>
                    <p className="subtitle" style={{fontWeight: 'bold', fontSize: '1.2rem'}}>{contract.doc_type} № {contract.unique_contract_number}</p>
                </div>
                <div className="header-right" style={{gap: '10px'}}>
                    <button onClick={handleOpenFolder} className="open-folder-btn" style={{padding: '10px 20px'}}>📂 Папка</button>
                    {!isEditing ? (
                        <><button onClick={() => setIsEditing(true)} className="confirm-btn" style={{backgroundColor: '#3498db', padding: '10px 20px'}}>✏️ Редактировать</button>
                        <button onClick={handleDelete} className="delete-btn" style={{padding: '10px 20px'}}>🗑️ Удалить</button></>
                    ) : (
                        <><button onClick={handleSave} className="confirm-btn" style={{padding: '10px 20px'}}>💾 Сохранить</button>
                        <button onClick={() => setIsEditing(false)} style={{background: 'none', color: '#666', fontWeight: 'bold'}}>Отмена</button></>
                    )}
                </div>
            </header>

            <div className="card" style={{borderTop: '4px solid #2c3e50', marginBottom: '20px'}}>
                <div className="form-grid" style={{gridTemplateColumns: 'repeat(6, 1fr)'}}>
                    <div><strong>Исполнитель</strong> <p style={{fontWeight: 'bold'}}>{contract.company}</p></div>
                    <div><strong>Статус</strong> <p><span className={`status-badge ${status.class}`}>{status.label}</span></p></div>
                    <div><strong>Сумма</strong> <p style={{fontWeight: 'bold'}}>{contract.contract_cost.toLocaleString()} ₽</p></div>
                    {contract.work_type === 'ТО' && <div><strong>В месяц</strong> <p style={{color: '#27ae60', fontWeight: 'bold'}}>{contract.monthly_cost?.toLocaleString()} ₽</p></div>}
                    <div><strong>Лифтов</strong> <p style={{fontWeight: 'bold'}}>{contract.elevator_count || elevatorList.length}</p></div>
                    <div><strong>Дата закл.</strong> <p>{contract.conclusion_date}</p></div>
                </div>
            </div>

            <div className="form-grid" style={{alignItems: 'start'}}>
                <div className="card" style={{gridColumn: 'span 2'}}>
                    <h3 className="form-group-title" style={{fontWeight: 'bold'}}>СРОКИ ДЕЙСТВИЯ</h3>
                    <div className="form-grid" style={{gridTemplateColumns: '1fr 1fr', marginBottom: '20px'}}>
                        <label><strong>Дата начала</strong><input type="date" disabled={!isEditing} value={isEditing ? editData.start_date : contract.start_date} onChange={e => setEditData({...editData, start_date: e.target.value})}/></label>
                        <label><strong>Дата окончания</strong><input type="date" disabled={!isEditing} value={isEditing ? editData.end_date : contract.end_date} onChange={e => setEditData({...editData, end_date: e.target.value})}/></label>
                    </div>

                    <div style={{marginTop: '25px', padding: '15px', background: '#fcfcfc', borderLeft: '4px solid #f39c12', borderRadius: '4px'}}>
                        <strong style={{fontSize: '0.85rem', color: '#7f8c8d', textTransform: 'uppercase'}}>Краткая сводка:</strong>
                        {isEditing ? (
                            <input style={{marginTop: '10px', width: '100%', padding: '8px'}} value={editData.ultra_short_summary || ''} onChange={e => setEditData({...editData, ultra_short_summary: e.target.value})}/>
                        ) : (
                            <p style={{marginTop: '5px', fontSize: '1.1rem', fontWeight: '600', color: '#2c3e50'}}>{contract.ultra_short_summary || 'Нет краткого описания'}</p>
                        )}
                    </div>

                    <h3 className="form-group-title" style={{fontWeight: 'bold', marginTop: '35px'}}>ИНФОРМАЦИЯ ОБ ОБЪЕКТЕ</h3>
                    <div className="form-grid" style={{gridTemplateColumns: '1fr'}}>
                        <label><strong>Адрес объекта</strong><input disabled={!isEditing} className="wide-input" value={isEditing ? editData.work_address : (contract.work_address || '')} onChange={e => setEditData({...editData, work_address: e.target.value})}/></label>
                        <div style={{marginTop: '15px'}}>
                            <strong>Список лифтов</strong>
                            {isEditing ? (
                                <textarea style={{marginTop: '10px', width: '100%'}} rows="5" value={editData.elevator_addresses || ''} onChange={e => setEditData({...editData, elevator_addresses: e.target.value})}/>
                            ) : (
                                <div className="elevator-list-box" style={{marginTop: '10px', maxHeight: '200px', overflowY: 'auto', background: '#f8f9fa', padding: '15px', borderRadius: '4px'}}>
                                    {elevatorList.length > 0 ? (
                                        <ul style={{listStyle: 'none', padding: 0, margin: 0}}>
                                            {elevatorList.map((addr, idx) => <li key={idx} style={{padding: '5px 0', borderBottom: '1px solid #eee'}}>{idx+1}. {addr}</li>)}
                                        </ul>
                                    ) : <p style={{color: '#999'}}>Нет данных</p>}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="card" style={{gridColumn: 'span 1'}}>
                    <h3 className="form-group-title">ЗАКАЗЧИК</h3>
                    <p style={{fontWeight: 'bold', fontSize: '1.1rem'}}>{contract.customer}</p>
                    <div style={{marginTop: '10px', fontSize: '0.9rem', lineHeight: '1.6'}}>
                        <div><strong>ИНН:</strong> {customer?.inn}</div>
                        <div><strong>ОГРН:</strong> {customer?.ogrn}</div>
                        <div><strong>Директор:</strong> {customer?.ceo_name}</div>
                    </div>
                    <button onClick={() => navigate(`/customer/${contract.customer_id}`)} style={{marginTop: '20px', background: '#f8f9fa', color: '#3498db', width: '100%', border: '1px solid #ddd'}}>Карточка компании</button>
                    
                    <h3 className="form-group-title" style={{marginTop: '30px'}}>ПОДРОБНОЕ РЕЗЮМЕ</h3>
                    <textarea 
                        disabled={!isEditing} 
                        rows="15" 
                        style={{minHeight: '350px', width: '100%', marginTop: '10px', fontSize: '0.9rem', lineHeight: '1.5', border: 'none', background: isEditing ? '#fff' : '#fcfcfc'}}
                        value={isEditing ? editData.short_description : contract.short_description} 
                        onChange={e => setEditData({...editData, short_description: e.target.value})}
                    />
                </div>
            </div>
        </div>
    );
}

export default ContractDetails;
