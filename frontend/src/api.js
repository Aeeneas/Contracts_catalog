const API_BASE_URL = 'http://localhost:8000';

export const api = {
    async fetch(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP Error ${response.status}`);
        }
        return response.json();
    },

    getContracts: () => api.fetch('/contracts'),
    getContract: (id) => api.fetch(`/contracts/${id}`),
    updateContract: (id, data) => api.fetch(`/contracts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteContract: (id) => api.fetch(`/contracts/${id}`, { method: 'DELETE' }),
    openContractFolder: (id) => api.fetch(`/contracts/${id}/open-folder`, { method: 'POST' }),

    getCustomers: () => api.fetch('/customers'),
    getCustomer: (id) => api.fetch(`/customers/${id}`),
    updateCustomer: (id, data) => api.fetch(`/customers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

    openRootFolder: () => api.fetch('/open-folder', { method: 'POST' }),
    resetSystem: () => api.fetch('/reset-system', { method: 'POST' }),
};
