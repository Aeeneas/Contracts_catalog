import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './ContractDetails.css'; // Будет создан позже

function ContractDetails() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [contract, setContract] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchContractDetails = async () => {
            try {
                const response = await fetch(`http://localhost:8000/contracts/${id}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                setContract(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchContractDetails();
    }, [id]);

    if (loading) return <p className="details-loading">Загрузка деталей договора...</p>;
    if (error) return <p className="details-error">Ошибка при загрузке деталей: {error}</p>;
    if (!contract) return <p className="details-not-found">Договор не найден.</p>;

    return (
        <div className="contract-details-container">
            <button onClick={() => navigate('/')} className="back-button">
                &larr; Назад к списку
            </button>
            <h2>Детали Договора: {contract.unique_contract_number}</h2>
            <div className="details-grid">
                <div className="detail-item">
                    <strong>ID:</strong> <span>{contract.id}</span>
                </div>
                <div className="detail-item">
                    <strong>Уникальный номер:</strong> <span>{contract.unique_contract_number}</span>
                </div>
                <div className="detail-item">
                    <strong>Компания:</strong> <span>{contract.company}</span>
                </div>
                <div className="detail-item">
                    <strong>Заказчик:</strong> <span>{contract.customer}</span>
                </div>
                <div className="detail-item">
                    <strong>Тип работ:</strong> <span>{contract.work_type}</span>
                </div>
                <div className="detail-item">
                    <strong>Стоимость договора:</strong> <span>{contract.contract_cost}</span>
                </div>
                <div className="detail-item">
                    <strong>Стоимость в месяц:</strong> <span>{contract.monthly_cost || 'N/A'}</span>
                </div>
                <div className="detail-item full-width">
                    <strong>Этапы выполнения:</strong> <span>{contract.stages_info}</span>
                </div>
                <div className="detail-item full-width">
                    <strong>Краткое описание:</strong> <span>{contract.short_description}</span>
                </div>
                <div className="detail-item">
                    <strong>Дата заключения:</strong> <span>{new Date(contract.conclusion_date).toLocaleDateString()}</span>
                </div>
                <div className="detail-item">
                    <strong>Дата начала:</strong> <span>{new Date(contract.start_date).toLocaleDateString()}</span>
                </div>
                <div className="detail-item">
                    <strong>Дата окончания:</strong> <span>{new Date(contract.end_date).toLocaleDateString()}</span>
                </div>
                <div className="detail-item full-width">
                    <strong>Путь в каталоге:</strong> <span>{contract.catalog_path}</span>
                </div>
                <div className="detail-item">
                    <strong>Дата загрузки:</strong> <span>{new Date(contract.upload_date).toLocaleDateString()}</span>
                </div>
                <div className="detail-item">
                    <strong>Статус AI анализа:</strong> <span>{contract.ai_analysis_status}</span>
                </div>
            </div>
        </div>
    );
}

export default ContractDetails;
