import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom'; // Добавлен импорт useNavigate
import './ContractList.css';

function ContractList() {
    const navigate = useNavigate(); // Инициализация useNavigate
    const [contracts, setContracts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');

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

    const filteredContracts = contracts.filter(contract =>
        contract.unique_contract_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
        contract.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
        contract.customer.toLowerCase().includes(searchTerm.toLowerCase()) ||
        contract.work_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
        contract.short_description.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const handleRowClick = (contractId) => {
        navigate(`/contract/${contractId}`); // Переход на страницу деталей
    };

    const handleOpenFolder = async (e, contractId) => {
        e.stopPropagation(); // Чтобы не срабатывал клик по строке (переход к деталям)
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
                            <th>Уник. номер</th>
                            <th>Компания</th>
                            <th>Заказчик</th>
                            <th>Тип работ</th>
                            <th>Стоимость</th>
                            <th>Дата заключения</th>
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
