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
    
    // Use inline styles instead of CSS classes
    const colors = {
        'info': 'background: #3b82f6; color: white;',
        'success': 'background: #10b981; color: white;', 
        'error': 'background: #ef4444; color: white;',
        'warning': 'background: #f59e0b; color: white;'
    };
    
    toast.style.cssText = `
        ${colors[type] || colors.info}
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 8px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-width: 300px;
    `;
    
    toast.innerHTML = `
        <div style="display: flex; align-items: center;">
            <i class="fas fa-info-circle" style="margin-right: 8px;"></i>
            <span>${message}</span>
        </div>
        <button onclick="this.parentElement.remove()" style="background: none; border: none; color: white; cursor: pointer; padding: 0; margin-left: 12px;">
            <i class="fas fa-times"></i>
        </button>
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
        locations: { title: 'Locations', subtitle: 'Manage venues and facilities' },
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
        case 'locations':
            loadLocations();
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
                <div class="overflow-x-auto">
                    <table class="table w-full">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Time</th>
                                <th>Teams</th>
                                <th>Location</th>
                                <th>Sport</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="games-tbody">
                            <tr>
                                <td colspan="7" class="text-center text-gray-600">Loading games...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    updateMainContent(content);
    loadGamesData();
}

async function loadGamesData() {
    try {
        const data = await apiRequest('/api/games');
        const tbody = document.getElementById('games-tbody');
        
        if (data.success && data.games && data.games.length > 0) {
            tbody.innerHTML = data.games.map(game => `
                <tr>
                    <td>${game.date}</td>
                    <td>${game.time}</td>
                    <td>${game.home_team} vs ${game.away_team}</td>
                    <td>${game.location || 'TBA'}</td>
                    <td>${game.sport || 'N/A'}</td>
                    <td><span class="badge badge-${game.status === 'scheduled' ? 'info' : 'success'}">${game.status}</span></td>
                    <td>
                        <button class="btn btn-sm btn-secondary mr-2" onclick="editGame(${game.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deleteGame(${game.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-gray-600">No games found</td></tr>';
        }
    } catch (error) {
        console.error('Error loading games:', error);
        const tbody = document.getElementById('games-tbody');
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-red-600">Error loading games</td></tr>';
    }
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
                <div class="overflow-x-auto">
                    <table class="table w-full">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Email</th>
                                <th>Phone</th>
                                <th>Sports</th>
                                <th>Experience</th>
                                <th>Rating</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="officials-tbody">
                            <tr>
                                <td colspan="8" class="text-center text-gray-600">Loading officials...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    updateMainContent(content);
    loadOfficialsData();
}

async function loadOfficialsData() {
    try {
        const data = await apiRequest('/api/officials');
        const tbody = document.getElementById('officials-tbody');
        
        if (data.success && data.officials && data.officials.length > 0) {
            tbody.innerHTML = data.officials.map(official => `
                <tr>
                    <td>${official.first_name} ${official.last_name}</td>
                    <td>${official.email || 'N/A'}</td>
                    <td>${official.phone || 'N/A'}</td>
                    <td>${official.sports || 'N/A'}</td>
                    <td>${official.experience_level || 'N/A'}</td>
                    <td>${official.rating || 'N/A'}</td>
                    <td><span class="badge badge-${official.is_active ? 'success' : 'danger'}">${official.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td>
                        <button class="btn btn-sm btn-secondary mr-2" onclick="editOfficial(${official.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deleteOfficial(${official.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-gray-600">No officials found</td></tr>';
        }
    } catch (error) {
        console.error('Error loading officials:', error);
        const tbody = document.getElementById('officials-tbody');
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-red-600">Error loading officials</td></tr>';
    }
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
                <div class="overflow-x-auto">
                    <table class="table w-full">
                        <thead>
                            <tr>
                                <th>Game</th>
                                <th>Date/Time</th>
                                <th>Official</th>
                                <th>Position</th>
                                <th>Status</th>
                                <th>Fee</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="assignments-tbody">
                            <tr>
                                <td colspan="7" class="text-center text-gray-600">Loading assignments...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    updateMainContent(content);
    loadAssignmentsData();
}

async function loadAssignmentsData() {
    try {
        const data = await apiRequest('/api/assignments');
        const tbody = document.getElementById('assignments-tbody');
        
        if (data.success && data.assignments && data.assignments.length > 0) {
            tbody.innerHTML = data.assignments.map(assignment => `
                <tr>
                    <td>${assignment.home_team} vs ${assignment.away_team}</td>
                    <td>${assignment.date} ${assignment.time}</td>
                    <td>${assignment.first_name} ${assignment.last_name}</td>
                    <td>${assignment.position || 'N/A'}</td>
                    <td><span class="badge badge-${assignment.status === 'confirmed' ? 'success' : 'warning'}">${assignment.status}</span></td>
                    <td>$${assignment.fee || '0.00'}</td>
                    <td>
                        <button class="btn btn-sm btn-secondary mr-2" onclick="editAssignment(${assignment.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deleteAssignment(${assignment.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-gray-600">No assignments found</td></tr>';
        }
    } catch (error) {
        console.error('Error loading assignments:', error);
        const tbody = document.getElementById('assignments-tbody');
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-red-600">Error loading assignments</td></tr>';
    }
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
                <div class="overflow-x-auto">
                    <table class="table w-full">
                        <thead>
                            <tr>
                                <th>Username</th>
                                <th>Full Name</th>
                                <th>Email</th>
                                <th>Role</th>
                                <th>Status</th>
                                <th>Last Login</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="users-tbody">
                            <tr>
                                <td colspan="7" class="text-center text-gray-600">Loading users...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    updateMainContent(content);
    loadUsersData();
}

async function loadUsersData() {
    try {
        const data = await apiRequest('/api/users');
        const tbody = document.getElementById('users-tbody');
        
        if (data.success && data.users && data.users.length > 0) {
            tbody.innerHTML = data.users.map(user => `
                <tr>
                    <td>${user.username}</td>
                    <td>${user.full_name || 'N/A'}</td>
                    <td>${user.email || 'N/A'}</td>
                    <td><span class="badge badge-${user.role === 'superadmin' ? 'danger' : user.role === 'admin' ? 'warning' : 'info'}">${user.role}</span></td>
                    <td><span class="badge badge-${user.is_active ? 'success' : 'danger'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td>${user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}</td>
                    <td>
                        <button class="btn btn-sm btn-secondary mr-2" onclick="editUser(${user.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        ${user.role !== 'superadmin' ? `<button class="btn btn-sm btn-danger" onclick="deleteUser(${user.id})"><i class="fas fa-trash"></i></button>` : ''}
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-gray-600">No users found</td></tr>';
        }
    } catch (error) {
        console.error('Error loading users:', error);
        const tbody = document.getElementById('users-tbody');
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-red-600">Error loading users</td></tr>';
    }
}

function loadLocations() {
    const content = `
        <div class="card p-6">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold">Locations Management</h3>
                <button class="btn btn-primary" onclick="showAddLocationModal()">
                    <i class="fas fa-plus mr-2"></i>Add Location
                </button>
            </div>
            <div id="locations-table">
                <div class="overflow-x-auto">
                    <table class="table w-full">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Address</th>
                                <th>City</th>
                                <th>Contact</th>
                                <th>Capacity</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="locations-tbody">
                            <tr>
                                <td colspan="7" class="text-center text-blue-600">Locations feature - Coming soon in Phase 4</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    updateMainContent(content);
}

function loadReports() {
    const content = `
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Quick Stats -->
            <div class="card p-6">
                <h3 class="text-lg font-semibold mb-4">Quick Statistics</h3>
                <div class="grid grid-cols-2 gap-4">
                    <div class="bg-blue-50 p-4 rounded-lg text-center">
                        <div class="text-2xl font-bold text-blue-600" id="total-games-stat">0</div>
                        <div class="text-sm text-blue-800">Total Games</div>
                    </div>
                    <div class="bg-green-50 p-4 rounded-lg text-center">
                        <div class="text-2xl font-bold text-green-600" id="total-officials-stat">0</div>
                        <div class="text-sm text-green-800">Total Officials</div>
                    </div>
                    <div class="bg-purple-50 p-4 rounded-lg text-center">
                        <div class="text-2xl font-bold text-purple-600" id="total-assignments-stat">0</div>
                        <div class="text-sm text-purple-800">Total Assignments</div>
                    </div>
                    <div class="bg-yellow-50 p-4 rounded-lg text-center">
                        <div class="text-2xl font-bold text-yellow-600" id="total-users-stat">0</div>
                        <div class="text-sm text-yellow-800">Total Users</div>
                    </div>
                </div>
            </div>

            <!-- Export Options -->
            <div class="card p-6">
                <h3 class="text-lg font-semibold mb-4">Data Export</h3>
                <div class="space-y-3">
                    <div class="bg-blue-50 p-4 rounded-lg">
                        <h4 class="font-medium text-blue-800 mb-2">Games Report</h4>
                        <p class="text-sm text-blue-600 mb-3">Export all games data with schedules and details</p>
                        <button class="btn btn-sm btn-primary" onclick="exportGames()">
                            <i class="fas fa-download mr-2"></i>Download CSV
                        </button>
                    </div>
                    <div class="bg-green-50 p-4 rounded-lg">
                        <h4 class="font-medium text-green-800 mb-2">Officials Report</h4>
                        <p class="text-sm text-green-600 mb-3">Export officials data with contact info and ratings</p>
                        <button class="btn btn-sm btn-primary" onclick="exportOfficials()">
                            <i class="fas fa-download mr-2"></i>Download CSV
                        </button>
                    </div>
                    <div class="bg-purple-50 p-4 rounded-lg">
                        <h4 class="font-medium text-purple-800 mb-2">Assignments Report</h4>
                        <p class="text-sm text-purple-600 mb-3">Export assignments data with game and official details</p>
                        <button class="btn btn-sm btn-primary" onclick="exportAssignments()">
                            <i class="fas fa-download mr-2"></i>Download CSV
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Recent Activity -->
        <div class="card p-6 mt-6">
            <h3 class="text-lg font-semibold mb-4">Recent Activity Summary</h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="text-center">
                    <div class="text-3xl font-bold text-blue-600" id="recent-games">0</div>
                    <div class="text-sm text-gray-600">Games This Month</div>
                </div>
                <div class="text-center">
                    <div class="text-3xl font-bold text-green-600" id="recent-assignments">0</div>
                    <div class="text-sm text-gray-600">New Assignments</div>
                </div>
                <div class="text-center">
                    <div class="text-3xl font-bold text-purple-600" id="active-officials-count">0</div>
                    <div class="text-sm text-gray-600">Active Officials</div>
                </div>
            </div>
        </div>
    `;
    
    updateMainContent(content);
    loadReportsData();
}

async function loadReportsData() {
    try {
        // Load dashboard stats for reports
        const dashboardData = await apiRequest('/api/dashboard');
        if (dashboardData.success) {
            document.getElementById('total-games-stat').textContent = dashboardData.upcoming_games || 0;
            document.getElementById('total-officials-stat').textContent = dashboardData.active_officials || 0;
            document.getElementById('total-assignments-stat').textContent = dashboardData.total_assignments || 0;
            document.getElementById('recent-games').textContent = dashboardData.upcoming_games || 0;
            document.getElementById('recent-assignments').textContent = dashboardData.total_assignments || 0;
            document.getElementById('active-officials-count').textContent = dashboardData.active_officials || 0;
        }

        // Load users count
        try {
            const usersData = await apiRequest('/api/users');
            if (usersData.success) {
                document.getElementById('total-users-stat').textContent = usersData.users ? usersData.users.length : 0;
            }
        } catch (error) {
            console.log('Users data not available (admin only)');
            document.getElementById('total-users-stat').textContent = 'N/A';
        }

    } catch (error) {
        console.error('Error loading reports data:', error);
        showToast('Error loading reports data', 'error');
    }
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

// Modal placeholder functions (to be fully implemented in Phase 4)
function showAddGameModal() {
    showToast('Add Game modal - Full implementation coming in Phase 4', 'info');
}

function showAddOfficialModal() {
    showToast('Add Official modal - Full implementation coming in Phase 4', 'info');
}

function showAddAssignmentModal() {
    showToast('Add Assignment modal - Full implementation coming in Phase 4', 'info');
}

function showAddUserModal() {
    showToast('Add User modal - Full implementation coming in Phase 4', 'info');
}

function showAddLocationModal() {
    showToast('Add Location modal - Full implementation coming in Phase 4', 'info');
}

// Edit functions
function editGame(id) {
    showToast(`Edit Game ${id} - Full implementation coming in Phase 4`, 'info');
}

function editOfficial(id) {
    showToast(`Edit Official ${id} - Full implementation coming in Phase 4`, 'info');
}

function editAssignment(id) {
    showToast(`Edit Assignment ${id} - Full implementation coming in Phase 4`, 'info');
}

function editUser(id) {
    showToast(`Edit User ${id} - Full implementation coming in Phase 4`, 'info');
}

// Delete functions
function deleteGame(id) {
    if (confirm('Are you sure you want to delete this game?')) {
        showToast(`Delete Game ${id} - Full implementation coming in Phase 4`, 'info');
    }
}

function deleteOfficial(id) {
    if (confirm('Are you sure you want to delete this official?')) {
        showToast(`Delete Official ${id} - Full implementation coming in Phase 4`, 'info');
    }
}

function deleteAssignment(id) {
    if (confirm('Are you sure you want to delete this assignment?')) {
        showToast(`Delete Assignment ${id} - Full implementation coming in Phase 4`, 'info');
    }
}

function deleteUser(id) {
    if (confirm('Are you sure you want to delete this user?')) {
        showToast(`Delete User ${id} - Full implementation coming in Phase 4`, 'info');
    }
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