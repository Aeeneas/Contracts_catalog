import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

const CustomerDetails = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [customer, setCustomer] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(false);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [editForm, setEditForm] = useState({});

    useEffect(() => {
        fetchCustomerDetails();
    }, [id]);

    const fetchCustomerDetails = async () => {
        try {
            const response = await fetch(`http://localhost:8000/customers/${id}`);
            if (!response.ok) throw new Error('Заказчик не найден');
            const data = await response.json();
            setCustomer(data);
            setEditForm(data);
            setLoading(false);
        } catch (error) {
            console.error('Ошибка:', error);
            setLoading(false);
        }
    };

    const handleRefreshDadata = async () => {
        setIsRefreshing(true);
        try {
            const response = await fetch(`http://localhost:8000/customers/${id}/refresh-dadata`, {
                method: 'POST'
            });
            if (response.ok) {
                const updated = await response.json();
                setCustomer(updated);
                setEditForm(updated);
                alert('Данные успешно обновлены из DaData');
            } else {
                alert('Не удалось получить данные из DaData');
            }
        } catch (error) {
            alert('Ошибка сети');
        } finally {
            setIsRefreshing(false);
        }
    };

    const handleSave = async () => {
        try {
            const response = await fetch(`http://localhost:8000/customers/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(editForm)
            });
            if (response.ok) {
                const updated = await response.json();
                setCustomer(updated);
                setIsEditing(false);
                alert('Данные сохранены');
            }
        } catch (error) { alert('Ошибка при сохранении'); }
    };

    if (loading) return <div className="p-10 center-text">Загрузка...</div>;
    if (!customer) return <div className="p-10 center-text">Заказчик не найден</div>;

    return (
        <div className="page-container">
            <header className="home-header">
                <div className="header-left">
                    <button onClick={() => navigate('/customers')} style={{background: 'none', color: '#3498db', padding: 0, marginBottom: '10px', fontWeight: 'bold'}}>← Назад к списку</button>
                    <h1>{customer.name}</h1>
                    <p className="subtitle">Карточка контрагента ИНН: {customer.inn}</p>
                </div>
                <div className="header-right" style={{gap: '10px'}}>
                    <button 
                        onClick={handleRefreshDadata} 
                        className="open-folder-btn" 
                        disabled={isRefreshing}
                        style={{backgroundColor: '#2ecc71'}}
                    >
                        {isRefreshing ? 'Обновление...' : '🌐 Обновить из DaData'}
                    </button>
                    <button 
                        onClick={() => isEditing ? handleSave() : setIsEditing(true)} 
                        className="confirm-btn"
                    >
                        {isEditing ? 'Сохранить' : 'Редактировать'}
                    </button>
                </div>
            </header>

            <div className="card" style={{borderLeft: '6px solid #3498db'}}>
                {isEditing ? (
                    <div className="form-grid">
                        <label className="full-width">Название компании
                            <input value={editForm.name || ''} onChange={e => setEditForm({...editForm, name: e.target.value})}/>
                        </label>
                        <label>ИНН <input disabled value={editForm.inn || ''} onChange={e => setEditForm({...editForm, inn: e.target.value})}/></label>
                        <label>ОГРН <input value={editForm.ogrn || ''} onChange={e => setEditForm({...editForm, ogrn: e.target.value})}/></label>
                        <label className="full-width">Директор <input value={editForm.ceo_name || ''} onChange={e => setEditForm({...editForm, ceo_name: e.target.value})}/></label>
                        <label className="full-width">Юридический адрес <input value={editForm.legal_address || ''} onChange={e => setEditForm({...editForm, legal_address: e.target.value})}/></label>
                        <label className="full-width">Контакты <input value={editForm.contact_info || ''} onChange={e => setEditForm({...editForm, contact_info: e.target.value})}/></label>
                        <label className="full-width">Реквизиты <textarea value={editForm.bank_details || ''} onChange={e => setEditForm({...editForm, bank_details: e.target.value})} rows="3"/></label>
                        <button onClick={() => setIsEditing(false)} style={{background: 'none', color: '#666', textDecoration: 'underline'}}>Отмена</button>
                    </div>
                ) : (
                    <div className="form-grid" style={{gridTemplateColumns: 'repeat(3, 1fr)'}}>
                        <div><strong>ИНН</strong> <p>{customer.inn}</p></div>
                        <div><strong>ОГРН</strong> <p>{customer.ogrn || '—'}</p></div>
                        <div><strong>Директор</strong> <p>{customer.ceo_name || '—'}</p></div>
                        <div className="full-width"><strong>Юридический адрес</strong> <p>{customer.legal_address || '—'}</p></div>
                        <div className="full-width"><strong>Контакты</strong> <p>{customer.contact_info || '—'}</p></div>
                        <div className="full-width"><strong>Реквизиты</strong> <pre style={{whiteSpace: 'pre-wrap', font: 'inherit'}}>{customer.bank_details || '—'}</pre></div>
                    </div>
                )}
            </div>

            <h2 style={{textAlign: 'left', marginTop: '40px', marginBottom: '20px'}}>Связанные договоры ({customer.contracts?.length || 0})</h2>
            <div className="table-scroll-wrapper">
                <table className="contracts-table">
                    <thead>
                        <tr>
                            <th>Номер</th>
                            <th>Тип</th>
                            <th>Вид работ</th>
                            <th>Сумма</th>
                            <th>Дата</th>
                            <th>Статус</th>
                        </tr>
                    </thead>
                    <tbody>
                        {customer.contracts?.map(contract => (
                            <tr key={contract.id} className="contract-row" onClick={() => navigate(`/contract/${contract.id}`)}>
                                <td style={{fontWeight: 'bold', color: '#3498db'}}>{contract.unique_contract_number}</td>
                                <td>{contract.doc_type}</td>
                                <td>{contract.work_type}</td>
                                <td>{contract.contract_cost?.toLocaleString()} ₽</td>
                                <td>{contract.conclusion_date}</td>
                                <td><span className="status-badge status-completed">Завершен</span></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default CustomerDetails;
