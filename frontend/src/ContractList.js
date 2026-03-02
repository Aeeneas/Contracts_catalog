import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './ContractList.css';

function ContractList() {
    const navigate = useNavigate();
    const [contracts, setContracts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortConfig, setSortConfig] = useState({ key: 'conclusion_date', direction: 'desc' });
    
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

    const handleSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const toggleWorkType = (type) => {
        setActiveWorkTypes(prev => prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]);
    };

    const toggleCompany = (company) => {
        setActiveCompanies(prev => prev.includes(company) ? prev.filter(c => c !== company) : [...prev, company]);
    };

    const getSortIcon = (key) => {
        if (sortConfig.key !== key) return <span className="sort-icon">↕</span>;
        return <span className="sort-icon">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>;
    };

    const filteredContracts = contracts.filter(contract => {
        const matchesSearch = 
            (contract.unique_contract_number || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
            (contract.customer || '').toLowerCase().includes(searchTerm.toLowerCase());
        
        const matchesType = activeWorkTypes.length === 0 || activeWorkTypes.includes(contract.work_type);
        const matchesCompany = activeCompanies.length === 0 || activeCompanies.includes(contract.company);

        return matchesSearch && matchesType && matchesCompany;
    });

    const processedContracts = React.useMemo(() => {
        let sortable = [...filteredContracts];
        if (sortConfig.key) {
            sortable.sort((a, b) => {
                let aVal = a[sortConfig.key];
                let bVal = b[sortConfig.key];
                if (aVal === null || aVal === undefined) return 1;
                if (bVal === null || bVal === undefined) return -1;
                if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
                if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
                return 0;
            });
        }
        return sortable;
    }, [filteredContracts, sortConfig]);

    const getStatusInfo = (endDateStr) => {
        if (!endDateStr) return { label: 'Неопределено', class: 'status-undefined' };
        const today = new Date(); today.setHours(0, 0, 0, 0);
        const endDate = new Date(endDateStr);
        if (isNaN(endDate.getTime())) return { label: 'Неопределено', class: 'status-undefined' };
        return today <= endDate ? { label: 'Действует', class: 'status-active' } : { label: 'Завершен', class: 'status-ended' };
    };

    const handleOpenFolder = async (e, contractId) => {
        e.stopPropagation();
        try {
            await fetch(`http://localhost:8000/contracts/${contractId}/open-folder`, { method: 'POST' });
        } catch (err) { alert('Ошибка'); }
    };

    if (loading) return <div className="p-10 center-text">Загрузка...</div>;

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
                    {(activeWorkTypes.length > 0 || activeCompanies.length > 0) && (
                        <button className="filter-clear-btn" onClick={() => {setActiveWorkTypes([]); setActiveCompanies([]);}}>Сбросить ×</button>
                    )}
                </div>
            </div>

            <div className="table-scroll-wrapper">
                <table className="contracts-table">
                    <thead>
                        <tr>
                            <th onClick={() => handleSort('unique_contract_number')} style={{cursor: 'pointer'}}>
                                <div className="header-cell-content">Номер {getSortIcon('unique_contract_number')}</div>
                            </th>
                            <th onClick={() => handleSort('company')} style={{cursor: 'pointer'}}>
                                <div className="header-cell-content">Исполнитель {getSortIcon('company')}</div>
                            </th>
                            <th onClick={() => handleSort('customer')} style={{cursor: 'pointer'}}>
                                <div className="header-cell-content">Заказчик {getSortIcon('customer')}</div>
                            </th>
                            <th onClick={() => handleSort('work_type')} style={{cursor: 'pointer'}}>
                                <div className="header-cell-content">Вид работ {getSortIcon('work_type')}</div>
                            </th>
                            <th onClick={() => handleSort('contract_cost')} style={{cursor: 'pointer'}}>
                                <div className="header-cell-content">Стоимость {getSortIcon('contract_cost')}</div>
                            </th>
                            <th onClick={() => handleSort('conclusion_date')} style={{cursor: 'pointer'}}>
                                <div className="header-cell-content">Дата {getSortIcon('conclusion_date')}</div>
                            </th>
                            <th style={{width: '20%'}}>
                                <div className="header-cell-content">Сводка</div>
                            </th>
                            <th>
                                <div className="header-cell-content">Статус</div>
                            </th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {processedContracts.map(contract => {
                            const status = getStatusInfo(contract.end_date);
                            return (
                                <tr key={contract.id} onClick={() => navigate(`/contract/${contract.id}`)} className="contract-row">
                                    <td>{contract.unique_contract_number}</td>
                                    <td>{contract.company}</td>
                                    <td style={{fontWeight: '700'}}>{contract.customer}</td>
                                    <td>{contract.work_type}</td>
                                    <td style={{whiteSpace: 'nowrap'}}>{contract.contract_cost.toLocaleString()} ₽</td>
                                    <td>{new Date(contract.conclusion_date).toLocaleDateString()}</td>
                                    <td style={{fontSize: '0.85rem', color: '#666', fontStyle: 'italic'}}>{contract.ultra_short_summary || '—'}</td>
                                    <td><span className={`status-badge ${status.class}`}>{status.label}</span></td>
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
