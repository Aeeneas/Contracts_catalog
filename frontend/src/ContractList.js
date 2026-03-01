import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom'; // Добавлен импорт useNavigate
import './ContractList.css';

function ContractList() {
    const navigate = useNavigate();
    const [contracts, setContracts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortConfig, setSortConfig] = useState({ key: 'upload_date', direction: 'desc' }); // По умолчанию новые сверху

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

                if (aValue < bValue) {
                    return sortConfig.direction === 'asc' ? -1 : 1;
                }
                if (aValue > bValue) {
                    return sortConfig.direction === 'asc' ? 1 : -1;
                }
                return 0;
            });
        }
        return sortableContracts;
    }, [contracts, sortConfig]);

    const filteredContracts = sortedContracts.filter(contract =>
        contract.unique_contract_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
        contract.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
        contract.customer.toLowerCase().includes(searchTerm.toLowerCase()) ||
        contract.work_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
        contract.short_description.toLowerCase().includes(searchTerm.toLowerCase())
    );

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
            <h2>Список Договоров</h2>
            <input
                type="text"
                placeholder="Поиск по договорам..."
                className="search-input"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
            />
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
                            <th>Краткое описание</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredContracts.map(contract => (
                            <tr key={contract.id} onClick={() => handleRowClick(contract.id)} className="contract-row">
                                <td>{contract.unique_contract_number}</td>
                                <td>{contract.company}</td>
                                <td>{contract.customer}</td>
                                <td>{contract.work_type}</td>
                                <td>{contract.contract_cost}</td>
                                <td>{new Date(contract.conclusion_date).toLocaleDateString()}</td>
                                <td>{contract.short_description.substring(0, 100)}...</td>
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
