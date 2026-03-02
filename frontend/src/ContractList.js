import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './ContractList.css';

function ContractList() {
    const navigate = useNavigate();
    const [contracts, setContracts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortConfig, setSortConfig] = useState({ key: 'upload_date', direction: 'desc' });
    
    const [activeWorkTypes, setActiveWorkTypes] = useState([]); 
    const [activeCompanies, setActiveCompanies] = useState([]);

    const workTypes = ["ТО", "МОНТАЖ", "СТРОЙКА", "ПРОЕКТИРОВАНИЕ", "КАПИТАЛЬНЫЕ РАБОТЫ"];
    const companies = ["ТОР-ЛИФТ", "Противовес", "Противовес-Т"];

    useEffect(() => {
        const fetchContracts = async () => {
            try {
                const response = await fetch('http://localhost:8000/contracts');
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const data = await response.json();
                setContracts(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchContracts();
    }, []);

    const toggleWorkType = (type) => {
        setActiveWorkTypes(prev => prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]);
    };

    const toggleCompany = (company) => {
        setActiveCompanies(prev => prev.includes(company) ? prev.filter(c => c !== company) : [...prev, company]);
    };

    const handleSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
        setSortConfig({ key, direction });
    };

    const sortedContracts = React.useMemo(() => {
        let sortableContracts = [...contracts];
        if (sortConfig.key !== null) {
            sortableContracts.sort((a, b) => {
                const aValue = a[sortConfig.key];
                const bValue = b[sortConfig.key];
                if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
                if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
                return 0;
            });
        }
        return sortableContracts;
    }, [contracts, sortConfig]);

    const filteredContracts = sortedContracts.filter(contract => {
        const matchesSearch = 
            contract.unique_contract_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
            contract.customer.toLowerCase().includes(searchTerm.toLowerCase());
        
        const matchesType = activeWorkTypes.length === 0 || activeWorkTypes.includes(contract.work_type);
        const matchesCompany = activeCompanies.length === 0 || activeCompanies.includes(contract.company);

        return matchesSearch && matchesType && matchesCompany;
    });

    const getStatusInfo = (endDateStr) => {
        if (!endDateStr) return { label: 'Неопределено', class: 'status-undefined' };
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const endDate = new Date(endDateStr);
        if (isNaN(endDate.getTime())) return { label: 'Неопределено', class: 'status-undefined' };
        if (today <= endDate) {
            return { label: 'Действует', class: 'status-active' };
        } else {
            return { label: 'Завершен', class: 'status-ended' };
        }
    };

    const handleOpenFolder = async (e, contractId) => {
        e.stopPropagation();
        try {
            await fetch(`http://localhost:8000/contracts/${contractId}/open-folder`, { method: 'POST' });
        } catch (err) { alert('Ошибка'); }
    };

    if (loading) return <p>Загрузка договоров...</p>;
    if (error) return <p>Ошибка: {error}</p>;

    return (
        <div className="contract-list-container">
            <div className="filter-section">
                <div className="search-wrapper">
                    <input
                        type="text"
                        placeholder="Поиск по номеру или заказчику..."
                        className="search-input"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
                
                <div className="filter-group">
                    <div className="work-type-filters">
                        <span className="filter-label">Вид работ:</span>
                        {workTypes.map(type => (
                            <button key={type} className={`filter-chip ${activeWorkTypes.includes(type) ? 'active' : ''}`} onClick={() => toggleWorkType(type)}>{type}</button>
                        ))}
                    </div>
                    <div className="company-filters">
                        <span className="filter-label">Исполнитель:</span>
                        {companies.map(comp => (
                            <button key={comp} className={`filter-chip chip-company ${activeCompanies.includes(comp) ? 'active' : ''}`} onClick={() => toggleCompany(comp)}>{comp}</button>
                        ))}
                    </div>
                </div>
            </div>

            <div className="table-scroll-wrapper">
                <table className="contracts-table">
                    <thead>
                        <tr>
                            <th onClick={() => handleSort('unique_contract_number')}>Номер</th>
                            <th onClick={() => handleSort('company')}>Исполнитель</th>
                            <th onClick={() => handleSort('customer')}>Заказчик</th>
                            <th onClick={() => handleSort('work_type')}>Тип работ</th>
                            <th onClick={() => handleSort('contract_cost')}>Стоимость</th>
                            <th onClick={() => handleSort('conclusion_date')}>Дата</th>
                            <th style={{width: '25%'}}>Сводка</th>
                            <th>Статус</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredContracts.map(contract => {
                            const status = getStatusInfo(contract.end_date);
                            return (
                                <tr key={contract.id} onClick={() => navigate(`/contract/${contract.id}`)} className="contract-row">
                                    <td>{contract.unique_contract_number}</td>
                                    <td>{contract.company}</td>
                                    <td style={{fontWeight: 'bold'}}>{contract.customer}</td>
                                    <td>{contract.work_type}</td>
                                    <td style={{whiteSpace: 'nowrap'}}>{contract.contract_cost.toLocaleString()} ₽</td>
                                    <td>{new Date(contract.conclusion_date).toLocaleDateString()}</td>
                                    <td style={{fontSize: '0.85rem', color: '#666', fontStyle: 'italic'}}>
                                        {contract.ultra_short_summary || '—'}
                                    </td>
                                    <td>
                                        <span className={`status-badge ${status.class}`}>
                                            {status.label}
                                        </span>
                                    </td>
                                    <td>
                                        <button className="row-open-folder-btn" onClick={(e) => handleOpenFolder(e, contract.id)}>📂</button>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default ContractList;
