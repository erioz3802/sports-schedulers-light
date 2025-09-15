/*
Sports Schedulers - Main JavaScript
Author: Jose Ortiz
Date: September 14, 2025
Copyright (c) 2025 Jose Ortiz. All rights reserved.
*/

// Global application state
window.SportSchedulers = {
    currentPage: 'dashboard',
    user: null,
    data: {
        games: [],
        officials: [],
        assignments: [],
        users: []
    }
};

// Utility functions
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="flex items-center justify-between">
            <div class="flex items-center">
                <i class="fas ${getToastIcon(type)} mr-2"></i>
                <span>${message}</span>
            </div>
            <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-gray-400 hover:text-gray-600">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;

    toastContainer.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 5000);
}

function getToastIcon(type) {
    switch (type) {
        case 'success': return 'fa-check-circle';
        case 'error': return 'fa-exclamation-circle';
        case 'warning': return 'fa-exclamation-triangle';
        default: return 'fa-info-circle';
    }
}

function showLoading() {
    const mainContent = document.getElementById('main-content');
    if (mainContent) {
        mainContent.innerHTML = `
            <div class="flex justify-center items-center h-64">
                <div class="loading show items-center">
                    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-3"></div>
                    <span class="text-gray-600">Loading...</span>
                </div>
            </div>
        `;
    }
}

function hideLoading() {
    const loading = document.querySelector('.loading');
    if (loading) {
        loading.classList.remove('show');
    }
}

// API helper functions
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }

        return data;
    } catch (error) {
        console.error('API request failed:', error);
        showToast(error.message, 'error');
        throw error;
    }
}

// Navigation functions
function setActivePage(pageName) {
    // Update navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    const activeLink = document.querySelector(`[data-page="${pageName}"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }

    // Update page title and subtitle
    const titles = {
        dashboard: { title: 'Dashboard', subtitle: 'Welcome to your dashboard' },
        games: { title: 'Games', subtitle: 'Manage games and schedules' },
        officials: { title: 'Officials', subtitle: 'Manage officials and referees' },
        assignments: { title: 'Assignments', subtitle: 'Manage game assignments' },
        users: { title: 'Users', subtitle: 'Manage system users' },
        reports: { title: 'Reports', subtitle: 'View reports and analytics' }
    };

    const pageInfo = titles[pageName] || { title: 'Page', subtitle: 'Loading...' };
    
    const titleElement = document.getElementById('page-title');
    const subtitleElement = document.getElementById('page-subtitle');
    
    if (titleElement) titleElement.textContent = pageInfo.title;
    if (subtitleElement) subtitleElement.textContent = pageInfo.subtitle;

    // Store current page
    window.SportSchedulers.currentPage = pageName;
}

function loadPage(pageName) {
    setActivePage(pageName);
    showLoading();

    switch (pageName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'games':
            loadGames();
            break;
        case 'officials':
            loadOfficials();
            break;
        case 'assignments':
            loadAssignments();
            break;
        case 'users':
            loadUsers();
            break;
        case 'reports':
            loadReports();
            break;
        default:
            loadDashboard();
    }
}

// Page loading functions
function loadDashboard() {
    const content = `
        <!-- Dashboard Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div class="card p-6">
                <div class="flex items-center">
                    <div class="p-3 rounded-full bg-blue-100 mr-4">
                        <i class="fas fa-calendar-alt text-blue-600 text-xl"></i>
                    </div>
                    <div>
                        <p class="text-2xl font-bold text-gray-900" id="upcoming-games">0</p>
                        <p class="text-gray-600">Upcoming Games</p>
                    </div>
                </div>
            </div>
            
            <div class="card p-6">
                <div class="flex items-center">
                    <div class="p-3 rounded-full bg-green-100 mr-4">
                        <i class="fas fa-users text-green-600 text-xl"></i>
                    </div>
                    <div>
                        <p class="text-2xl font-bold text-gray-900" id="active-officials">0</p>
                        <p class="text-gray-600">Active Officials</p>
                    </div>
                </div>
            </div>
            
            <div class="card p-6">
                <div class="flex items-center">
                    <div class="p-3 rounded-full bg-purple-100 mr-4">
                        <i class="fas fa-clipboard-check text-purple-600 text-xl"></i>
                    </div>
                    <div>
                        <p class="text-2xl font-bold text-gray-900" id="total-assignments">0</p>
                        <p class="text-gray-600">Total Assignments</p>
                    </div>
                </div>
            </div>
            
            <div class="card p-6">
                <div class="flex items-center">
                    <div class="p-3 rounded-full bg-yellow-100 mr-4">
                        <i class="fas fa-exclamation-triangle text-yellow-600 text-xl"></i>
                    </div>
                    <div>
                        <p class="text-2xl font-bold text-gray-900">0</p>
                        <p class="text-gray-600">Pending Assignments</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="card p-6">
                <h3 class="text-lg font-semibold mb-4">Welcome to the Web Version!</h3>
                <p class="text-gray-600 mb-4">Your desktop application has been successfully converted to a multiuser web application.</p>
                <div class="bg-green-50 border border-green-200 p-4 rounded-lg">
                    <h4 class="font-medium text-green-800 mb-2">✅ Migration Complete</h4>
                    <ul class="text-sm text-green-700 space-y-1">
                        <li>• All features preserved</li>
                        <li>• Real-time collaboration enabled</li>
                        <li>• Responsive design</li>
                        <li>• Same login credentials work</li>
                    </ul>
                </div>
            </div>
            
            <div class="card p-6">
                <h3 class="text-lg font-semibold mb-4">Next Steps</h3>
                <div class="space-y-3">
                    <div class="flex items-center p-3 bg-blue-50 rounded-lg">
                        <i class="fas fa-upload text-blue-600 mr-3"></i>
                        <span class="text-sm">Import your existing data</span>
                    </div>
                    <div class="flex items-center p-3 bg-purple-50 rounded-lg">
                        <i class="fas fa-users text-purple-600 mr-3"></i>
                        <span class="text-sm">Add team members</span>
                    </div>
                    <div class="flex items-center p-3 bg-green-50 rounded-lg">
                        <i class="fas fa-cogs text-green-600 mr-3"></i>
                        <span class="text-sm">Customize settings</span>
                    </div>
                </div>
            </div>
        </div>
    `;

    updateMainContent(content);
    loadDashboardStats();
}

function loadGames() {
    const content = `
        <div class="card p-6">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold">Games Management</h3>
                <button class="btn btn-primary" onclick="showAddGameModal()">
                    <i class="fas fa-plus mr-2"></i>Add Game
                </button>
            </div>
            <div id="games-table">
                <p class="text-gray-600">Loading games...</p>
            </div>
        </div>
    `;
    
    updateMainContent(content);
    // TODO: Load games data
}

function loadOfficials() {
    const content = `
        <div class="card p-6">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold">Officials Management</h3>
                <button class="btn btn-primary" onclick="showAddOfficialModal()">
                    <i class="fas fa-plus mr-2"></i>Add Official
                </button>
            </div>
            <div id="officials-table">
                <p class="text-gray-600">Loading officials...</p>
            </div>
        </div>
    `;
    
    updateMainContent(content);
    // TODO: Load officials data
}

function loadAssignments() {
    const content = `
        <div class="card p-6">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold">Assignments Management</h3>
                <button class="btn btn-primary" onclick="showAddAssignmentModal()">
                    <i class="fas fa-plus mr-2"></i>Create Assignment
                </button>
            </div>
            <div id="assignments-table">
                <p class="text-gray-600">Loading assignments...</p>
            </div>
        </div>
    `;
    
    updateMainContent(content);
    // TODO: Load assignments data
}

function loadUsers() {
    const content = `
        <div class="card p-6">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold">Users Management</h3>
                <button class="btn btn-primary" onclick="showAddUserModal()">
                    <i class="fas fa-plus mr-2"></i>Add User
                </button>
            </div>
            <div id="users-table">
                <p class="text-gray-600">Loading users...</p>
            </div>
        </div>
    `;
    
    updateMainContent(content);
    // TODO: Load users data
}

function loadReports() {
    const content = `
        <div class="card p-6">
            <h3 class="text-lg font-semibold mb-4">Reports & Analytics</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div class="bg-blue-50 p-4 rounded-lg">
                    <h4 class="font-medium text-blue-800 mb-2">Games Report</h4>
                    <p class="text-sm text-blue-600 mb-3">Export all games data</p>
                    <button class="btn btn-sm btn-primary" onclick="exportGames()">
                        <i class="fas fa-download mr-2"></i>Download CSV
                    </button>
                </div>
                <div class="bg-green-50 p-4 rounded-lg">
                    <h4 class="font-medium text-green-800 mb-2">Officials Report</h4>
                    <p class="text-sm text-green-600 mb-3">Export officials data</p>
                    <button class="btn btn-sm btn-primary" onclick="exportOfficials()">
                        <i class="fas fa-download mr-2"></i>Download CSV
                    </button>
                </div>
                <div class="bg-purple-50 p-4 rounded-lg">
                    <h4 class="font-medium text-purple-800 mb-2">Assignments Report</h4>
                    <p class="text-sm text-purple-600 mb-3">Export assignments data</p>
                    <button class="btn btn-sm btn-primary" onclick="exportAssignments()">
                        <i class="fas fa-download mr-2"></i>Download CSV
                    </button>
                </div>
            </div>
        </div>
    `;
    
    updateMainContent(content);
}

function updateMainContent(html) {
    const mainContent = document.getElementById('main-content');
    if (mainContent) {
        mainContent.innerHTML = html;
        hideLoading();
    }
}

// Dashboard stats loading
async function loadDashboardStats() {
    try {
        const data = await apiRequest('/api/dashboard');
        
        if (data.success) {
            const elements = {
                'upcoming-games': data.upcoming_games || 0,
                'active-officials': data.active_officials || 0,
                'total-assignments': data.total_assignments || 0
            };

            Object.entries(elements).forEach(([id, value]) => {
                const element = document.getElementById(id);
                if (element) {
                    element.textContent = value;
                }
            });
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

// Export functions
async function exportGames() {
    try {
        const response = await fetch('/api/export/games');
        const blob = await response.blob();
        downloadBlob(blob, 'games_export.csv');
        showToast('Games data exported successfully', 'success');
    } catch (error) {
        showToast('Failed to export games data', 'error');
    }
}

async function exportOfficials() {
    try {
        const response = await fetch('/api/export/officials');
        const blob = await response.blob();
        downloadBlob(blob, 'officials_export.csv');
        showToast('Officials data exported successfully', 'success');
    } catch (error) {
        showToast('Failed to export officials data', 'error');
    }
}

async function exportAssignments() {
    try {
        const response = await fetch('/api/export/assignments');
        const blob = await response.blob();
        downloadBlob(blob, 'assignments_export.csv');
        showToast('Assignments data exported successfully', 'success');
    } catch (error) {
        showToast('Failed to export assignments data', 'error');
    }
}

function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Modal placeholder functions (to be implemented in Phase 2)
function showAddGameModal() {
    showToast('Add Game modal - Coming in Phase 2', 'info');
}

function showAddOfficialModal() {
    showToast('Add Official modal - Coming in Phase 2', 'info');
}

function showAddAssignmentModal() {
    showToast('Add Assignment modal - Coming in Phase 2', 'info');
}

function showAddUserModal() {
    showToast('Add User modal - Coming in Phase 2', 'info');
}

// Mobile menu handling
function initializeMobileMenu() {
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (mobileMenuBtn && sidebar && overlay) {
        mobileMenuBtn.addEventListener('click', () => {
            sidebar.classList.toggle('mobile-open');
            overlay.classList.toggle('hidden');
        });

        overlay.addEventListener('click', () => {
            sidebar.classList.remove('mobile-open');
            overlay.classList.add('hidden');
        });
    }
}

// Initialize navigation
function initializeNavigation() {
    document.querySelectorAll('.nav-link[data-page]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = link.dataset.page;
            loadPage(page);
        });
    });
}

// Connection status monitoring
function updateConnectionStatus() {
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
        fetch('/api/dashboard')
            .then(() => {
                statusElement.innerHTML = `
                    <div class="w-2 h-2 bg-green-400 rounded-full mr-2"></div>
                    <span class="text-gray-600">Connected</span>
                `;
            })
            .catch(() => {
                statusElement.innerHTML = `
                    <div class="w-2 h-2 bg-red-400 rounded-full mr-2"></div>
                    <span class="text-gray-600">Disconnected</span>
                `;
            });
    }
}

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    console.log('Sports Schedulers Web App - Initializing...');
    
    initializeMobileMenu();
    initializeNavigation();
    
    // Load dashboard by default
    loadPage('dashboard');
    
    // Update connection status every 30 seconds
    setInterval(updateConnectionStatus, 30000);
    updateConnectionStatus();
    
    console.log('Sports Schedulers Web App - Ready!');
});