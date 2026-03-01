import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom'; // Добавлен импорт useNavigate
import './ContractList.css';

function ContractList() {
    const navigate = useNavigate();
    const [contracts, setContracts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortConfig, setSortConfig] = useState({ key: 'upload_date', direction: 'desc' });
    
    // Состояние для активных типов работ
    const [activeWorkTypes, setActiveWorkTypes] = useState([]); 
    const [activeCompanies, setActiveCompanies] = useState([]); // Новое состояние для компаний

    const workTypes = ["ТО", "МОНТАЖ", "СТРОЙКА", "ПРОЕКТИРОВАНИЕ", "КАПИТАЛЬНЫЕ РАБОТЫ"];
    const companies = ["ТОР-ЛИФТ", "Противовес", "Противовес-Т"];

    useEffect(() => {
        const fetchContracts = async () => {
            try {
                const response = await fetch('http://localhost:8000/contracts');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
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
        setActiveWorkTypes(prev => 
            prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
        );
    };

    const toggleCompany = (company) => {
        setActiveCompanies(prev => 
            prev.includes(company) ? prev.filter(c => c !== company) : [...prev, company]
        );
    };

    const handleSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
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
            contract.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
            contract.customer.toLowerCase().includes(searchTerm.toLowerCase()) ||
            contract.work_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
            contract.short_description.toLowerCase().includes(searchTerm.toLowerCase());
        
        const matchesType = activeWorkTypes.length === 0 || activeWorkTypes.includes(contract.work_type);
        const matchesCompany = activeCompanies.length === 0 || activeCompanies.includes(contract.company);

        return matchesSearch && matchesType && matchesCompany;
    });

    const getRowClass = (workType) => {
        const map = {
            "ТО": "row-to",
            "МОНТАЖ": "row-montage",
            "СТРОЙКА": "row-build",
            "ПРОЕКТИРОВАНИЕ": "row-project",
            "КАПИТАЛЬНЫЕ РАБОТЫ": "row-cap"
        };
        return map[workType] || "";
    };

    const handleRowClick = (contractId) => {
        navigate(`/contract/${contractId}`);
    };

    const handleOpenFolder = async (e, contractId) => {
        e.stopPropagation();
        try {
            const response = await fetch(`http://localhost:8000/contracts/${contractId}/open-folder`, {
                method: 'POST'
            });
            if (!response.ok) {
                const errorData = await response.json();
                alert(`Ошибка: ${errorData.message || 'Не удалось открыть папку'}`);
            }
        } catch (err) {
            console.error('Ошибка при открытии папки договора:', err);
            alert('Ошибка сети при попытке открыть папку.');
        }
    };

    const getSortIcon = (key) => {
        if (sortConfig.key !== key) return ' ↕';
        return sortConfig.direction === 'asc' ? ' ↑' : ' ↓';
    };

    if (loading) return <p>Загрузка договоров...</p>;
    if (error) return <p>Ошибка при загрузке договоров: {error}</p>;

    return (
        <div className="contract-list-container">
            <div className="filter-section">
                <div className="search-wrapper">
                    <input
                        type="text"
                        placeholder="Поиск по договорам..."
                        className="search-input"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
                
                <div className="filter-group">
                    <div className="work-type-filters">
                        <span className="filter-label">Вид работ:</span>
                        {workTypes.map(type => (
                            <button 
                                key={type} 
                                className={`filter-chip chip-${getRowClass(type)} ${activeWorkTypes.includes(type) ? 'active' : ''}`}
                                onClick={() => toggleWorkType(type)}
                            >
                                {type}
                            </button>
                        ))}
                    </div>

                    <div className="company-filters">
                        <span className="filter-label">Наша компания:</span>
                        {companies.map(comp => (
                            <button 
                                key={comp} 
                                className={`filter-chip chip-company ${activeCompanies.includes(comp) ? 'active' : ''}`}
                                onClick={() => toggleCompany(comp)}
                            >
                                {comp}
                            </button>
                        ))}
                    </div>

                    {(activeWorkTypes.length > 0 || activeCompanies.length > 0) && (
                        <button className="filter-clear-btn" onClick={() => {setActiveWorkTypes([]); setActiveCompanies([]);}}>Сбросить все ×</button>
                    )}
                </div>
            </div>

            <div className="table-scroll-wrapper">
                <table className="contracts-table">
                    <thead>
                        <tr>
                            <th onClick={() => handleSort('unique_contract_number')} className={`sortable ${sortConfig.key === 'unique_contract_number' ? 'active' : ''}`}>
                                Уник. номер <span className="sort-icon">{getSortIcon('unique_contract_number')}</span>
                            </th>
                            <th onClick={() => handleSort('company')} className={`sortable ${sortConfig.key === 'company' ? 'active' : ''}`}>
                                Компания <span className="sort-icon">{getSortIcon('company')}</span>
                            </th>
                            <th onClick={() => handleSort('customer')} className={`sortable ${sortConfig.key === 'customer' ? 'active' : ''}`}>
                                Заказчик <span className="sort-icon">{getSortIcon('customer')}</span>
                            </th>
                            <th onClick={() => handleSort('work_type')} className={`sortable ${sortConfig.key === 'work_type' ? 'active' : ''}`}>
                                Тип работ <span className="sort-icon">{getSortIcon('work_type')}</span>
                            </th>
                            <th onClick={() => handleSort('contract_cost')} className={`sortable ${sortConfig.key === 'contract_cost' ? 'active' : ''}`}>
                                Стоимость <span className="sort-icon">{getSortIcon('contract_cost')}</span>
                            </th>
                            <th onClick={() => handleSort('conclusion_date')} className={`sortable ${sortConfig.key === 'conclusion_date' ? 'active' : ''}`}>
                                Дата заключения <span className="sort-icon">{getSortIcon('conclusion_date')}</span>
                            </th>
                            <th>Сводка</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredContracts.map(contract => (
                            <tr key={contract.id} onClick={() => handleRowClick(contract.id)} className={`contract-row ${getRowClass(contract.work_type)}`}>
                                <td>{contract.unique_contract_number}</td>
                                <td>{contract.company}</td>
                                <td>{contract.customer}</td>
                                <td>{contract.work_type}</td>
                                <td>{contract.contract_cost.toLocaleString()}</td>
                                <td>{new Date(contract.conclusion_date).toLocaleDateString()}</td>
                                <td className="ultra-summary-cell">{contract.ultra_short_summary || 'Нет описания'}</td>
                                <td>
                                    <button 
                                        className="row-open-folder-btn"
                                        onClick={(e) => handleOpenFolder(e, contract.id)}
                                        title="Открыть папку с договором"
                                    >
                                        📂
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default ContractList;
