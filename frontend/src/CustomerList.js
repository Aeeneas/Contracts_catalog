import React, { useState, useEffect } from 'react';

const CustomerList = ({ onSelectCustomer }) => {
    const [customers, setCustomers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        fetchCustomers();
    }, []);

    const fetchCustomers = async () => {
        try {
            const response = await fetch('http://localhost:8000/customers');
            const data = await response.json();
            setCustomers(data);
            setLoading(false);
        } catch (error) {
            console.error('Ошибка:', error);
            setLoading(false);
        }
    };

    const filteredCustomers = customers.filter(c => 
        c.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
        c.inn.includes(searchTerm)
    );

    if (loading) return <div className="p-10">Загрузка базы заказчиков...</div>;

    return (
        <div className="page-container">
            <header className="home-header">
                <div className="header-left">
                    <h1>База заказчиков</h1>
                    <p className="subtitle">Реестр всех контрагентов организации</p>
                </div>
                <div className="header-right">
                    <input 
                        type="text" 
                        placeholder="Поиск по названию или ИНН..." 
                        className="search-input-inline"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        style={{
                            padding: '10px 15px',
                            borderRadius: '4px',
                            border: '1px solid #dce4e8',
                            width: '300px',
                            fontSize: '0.9rem'
                        }}
                    />
                </div>
            </header>

            <div className="table-scroll-wrapper">
                <table className="contracts-table">
                    <thead>
                        <tr>
                            <th>Наименование</th>
                            <th>ИНН</th>
                            <th>ОГРН</th>
                            <th>Директор</th>
                            <th>Юридический адрес</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredCustomers.map(customer => (
                            <tr 
                                key={customer.id} 
                                onClick={() => onSelectCustomer(customer.id)}
                                className="contract-row"
                            >
                                <td style={{fontWeight: '700', color: '#3498db'}}>{customer.name}</td>
                                <td>{customer.inn}</td>
                                <td>{customer.ogrn || '—'}</td>
                                <td>{customer.ceo_name || '—'}</td>
                                <td style={{fontSize: '0.85rem', color: '#666'}}>
                                    {customer.legal_address ? (customer.legal_address.substring(0, 80) + '...') : '—'}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {filteredCustomers.length === 0 && (
                    <div style={{padding: '40px', textAlign: 'center', color: '#999'}}>Заказчики не найдены</div>
                )}
            </div>
        </div>
    );
};

export default CustomerList;
