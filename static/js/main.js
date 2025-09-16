/**
 * Sports Schedulers - Main JavaScript File
 * Phases 1-4 Complete Implementation
 * 
 * Author: Jose Ortiz / JES Baseball LLC
 * Date: September 15, 2025
 * Version: Phase 4 Complete
 * Features: Full CRUD Operations, Real-time Updates, Professional UI
 */

// ======================================
// GLOBAL VARIABLES AND CONSTANTS
// ======================================

let currentEditId = null;
let currentEditType = null;
let currentSection = 'dashboard';
let dropdownData = {};
let refreshInterval = null;

// Configuration
const CONFIG = {
    refreshInterval: 30000, // 30 seconds
    notificationTimeout: 5000,
    loadingTimeout: 10000,
    apiTimeout: 30000
};

// ======================================
// APPLICATION INITIALIZATION
// ======================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Sports Schedulers - Initializing Application...');
    
    // Initialize application
    initializeApplication();
    
    // Set up periodic refresh
    setupPeriodicRefresh();
    
    // Initialize event listeners
    setupEventListeners();
    
    console.log('✅ Application initialized successfully');
});

function initializeApplication() {
    // Load initial data
    loadDropdownData();
    loadDashboard();
    
    // Initialize UI components
    initializeModals();
    initializeTooltips();
    
    // Set up mobile responsiveness
    setupMobileHandlers();
}

function setupEventListeners() {
    // Form submissions
    document.addEventListener('submit', handleFormSubmit);
    
    // Modal events
    document.addEventListener('hidden.bs.modal', handleModalClosed);
    
    // Window resize
    window.addEventListener('resize', handleWindowResize);
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

function setupPeriodicRefresh() {
    // Refresh current section data every 30 seconds
    refreshInterval = setInterval(() => {
        if (document.visibilityState === 'visible') {
            refreshCurrentSection();
        }
    }, CONFIG.refreshInterval);
}

// ======================================
// UTILITY FUNCTIONS
// ======================================

function showLoading(show = true) {
    const spinner = document.querySelector('.loading-spinner');
    if (spinner) {
        spinner.style.display = show ? 'block' : 'none';
    }
}

function showNotification(message, type = 'success', timeout = CONFIG.notificationTimeout) {
    const container = document.querySelector('.toast-container');
    if (!container) {
        console.error('Toast container not found');
        return;
    }
    
    const toastId = 'toast-' + Date.now();
    const iconClass = getNotificationIcon(type);
    
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `toast toast-${type} show`;
    toast.setAttribute('role', 'alert');
    
    toast.innerHTML = `
        <div class="toast-body d-flex align-items-center">
            <i class="fas fa-${iconClass} me-2"></i>
            <span class="flex-grow-1">${message}</span>
            <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after timeout
    setTimeout(() => {
        if (document.getElementById(toastId)) {
            const bsToast = new bootstrap.Toast(document.getElementById(toastId));
            bsToast.hide();
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, 500);
        }
    }, timeout);
}

function getNotificationIcon(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

function formatDate(dateString) {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString();
}

function formatDateTime(dateString) {
    if (!dateString) return '';
    return new Date(dateString).toLocaleString();
}

function formatTime(timeString) {
    if (!timeString) return '';
    try {
        const [hours, minutes] = timeString.split(':');
        const date = new Date();
        date.setHours(parseInt(hours), parseInt(minutes));
        return date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    } catch (e) {
        return timeString;
    }
}

function getStatusBadge(status) {
    const statusClasses = {
        'scheduled': 'bg-primary',
        'pending': 'bg-warning',
        'confirmed': 'bg-success',
        'declined': 'bg-danger',
        'completed': 'bg-secondary',
        'active': 'bg-success',
        'inactive': 'bg-secondary'
    };
    
    const className = statusClasses[status] || 'bg-secondary';
    const displayStatus = status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown';
    return `<span class="badge ${className}">${displayStatus}</span>`;
}

function generateStarRating(rating) {
    const stars = [];
    const numRating = parseFloat(rating) || 0;
    
    for (let i = 1; i <= 5; i++) {
        if (i <= numRating) {
            stars.push('<i class="fas fa-star text-warning"></i>');
        } else if (i - 0.5 <= numRating) {
            stars.push('<i class="fas fa-star-half-alt text-warning"></i>');
        } else {
            stars.push('<i class="far fa-star text-warning"></i>');
        }
    }
    return stars.join('');
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ======================================
// API HELPER FUNCTIONS
// ======================================

async function fetchAPI(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
        timeout: CONFIG.apiTimeout
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, mergedOptions);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ======================================
// NAVIGATION FUNCTIONS
// ======================================

function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.add('hidden');
    });
    
    // Show selected section
    const targetSection = document.getElementById(sectionName + '-section');
    if (targetSection) {
        targetSection.classList.remove('hidden');
    }
    
    // Update navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    const activeLink = document.querySelector(`[onclick="showSection('${sectionName}')"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }
    
    // Update page title
    const titles = {
        'dashboard': 'Dashboard',
        'games': 'Games Management', 
        'officials': 'Officials Management',
        'assignments': 'Assignments Management',
        'locations': 'Locations Management',
        'users': 'Users Management',
        'reports': 'Reports & Analytics'
    };
    
    const pageTitle = document.getElementById('pageTitle');
    if (pageTitle) {
        pageTitle.textContent = titles[sectionName] || 'Sports Schedulers';
    }
    
    currentSection = sectionName;
    
    // Load section data
    loadSectionData(sectionName);
}

function loadSectionData(sectionName) {
    switch(sectionName) {
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
    }
}

function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.toggle('show');
    }
}

function refreshCurrentSection() {
    if (currentSection) {
        loadSectionData(currentSection);
    }
}

// ======================================
// DATA LOADING FUNCTIONS
// ======================================

async function loadDropdownData() {
    try {
        const data = await fetchAPI('/api/dropdown-data');
        
        if (data.success) {
            dropdownData = data.data;
            populateDropdowns();
        }
    } catch (error) {
        console.error('Error loading dropdown data:', error);
    }
}

function populateDropdowns() {
    // Populate sports dropdown
    const sportSelects = document.querySelectorAll('select[name="sport"]');
    sportSelects.forEach(select => {
        // Clear existing options except first
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }
        
        if (dropdownData.sports) {
            dropdownData.sports.forEach(sport => {
                const option = document.createElement('option');
                option.value = sport;
                option.textContent = sport;
                select.appendChild(option);
            });
        }
    });

    // Populate locations dropdown
    const locationSelects = document.querySelectorAll('select[name="location"]');
    locationSelects.forEach(select => {
        // Clear existing options except first
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }
        
        if (dropdownData.locations) {
            dropdownData.locations.forEach(location => {
                const option = document.createElement('option');
                option.value = location.name;
                option.textContent = location.name;
                select.appendChild(option);
            });
        }
    });

    // Populate officials dropdown for assignments
    const officialSelects = document.querySelectorAll('select[name="official_id"]');
    officialSelects.forEach(select => {
        // Clear existing options except first
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }
        
        if (dropdownData.officials) {
            dropdownData.officials.forEach(official => {
                const option = document.createElement('option');
                option.value = official.id;
                option.textContent = official.name;
                select.appendChild(option);
            });
        }
    });

    // Load games for assignment dropdown
    loadGamesForAssignment();
}

async function loadGamesForAssignment() {
    try {
        const data = await fetchAPI('/api/games');
        
        if (data.success) {
            const gameSelects = document.querySelectorAll('select[name="game_id"]');
            gameSelects.forEach(select => {
                // Clear existing options except first
                while (select.children.length > 1) {
                    select.removeChild(select.lastChild);
                }
                
                data.games.forEach(game => {
                    const option = document.createElement('option');
                    option.value = game.id;
                    option.textContent = `${game.date} ${game.time} - ${game.home_team} vs ${game.away_team}`;
                    select.appendChild(option);
                });
            });
        }
    } catch (error) {
        console.error('Error loading games for assignment:', error);
    }
}

// ======================================
// DASHBOARD FUNCTIONS
// ======================================

async function loadDashboard() {
    try {
        showLoading(true);
        const data = await fetchAPI('/api/dashboard');
        
        if (data.success) {
            updateDashboardStats(data.stats);
            updateRecentActivity(data.stats.recent_activity || []);
            updateGamesBySport(data.stats.games_by_sport || []);
        } else {
            showNotification('Failed to load dashboard data', 'error');
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showNotification('Error loading dashboard data', 'error');
    } finally {
        showLoading(false);
    }
}

function updateDashboardStats(stats) {
    // Update statistics cards
    const statElements = {
        'total-games': stats.total_games || 0,
        'total-officials': stats.total_officials || 0,
        'total-assignments': stats.total_assignments || 0,
        'pending-assignments': stats.pending_assignments || 0
    };
    
    Object.entries(statElements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

function updateRecentActivity(activities) {
    const container = document.getElementById('recent-activity-list');
    if (!container) return;
    
    if (activities.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">No recent activity</div>';
        return;
    }
    
    container.innerHTML = activities.slice(0, 5).map(activity => `
        <div class="d-flex align-items-center mb-3">
            <div class="flex-shrink-0">
                <i class="fas fa-${getActivityIcon(activity.action)} text-primary"></i>
            </div>
            <div class="flex-grow-1 ms-3">
                <div class="fw-semibold">${formatActionName(activity.action)}</div>
                <small class="text-muted">by ${activity.full_name || 'System'} • ${formatDateTime(activity.timestamp)}</small>
            </div>
        </div>
    `).join('');
}

function getActivityIcon(action) {
    const icons = {
        'LOGIN': 'sign-in-alt',
        'LOGOUT': 'sign-out-alt',
        'CREATE_GAME': 'plus-circle',
        'CREATE_OFFICIAL': 'user-plus',
        'CREATE_ASSIGNMENT': 'clipboard-list',
        'CREATE_USER': 'user-plus',
        'CREATE_LOCATION': 'map-marker-alt',
        'UPDATE_GAME': 'edit',
        'UPDATE_OFFICIAL': 'edit',
        'UPDATE_ASSIGNMENT': 'edit',
        'UPDATE_USER': 'edit',
        'UPDATE_LOCATION': 'edit',
        'DELETE_GAME': 'trash',
        'DELETE_OFFICIAL': 'trash',
        'DELETE_ASSIGNMENT': 'trash',
        'DELETE_USER': 'trash',
        'DELETE_LOCATION': 'trash',
        'EXPORT_GAMES': 'download',
        'EXPORT_OFFICIALS': 'download',
        'EXPORT_ASSIGNMENTS': 'download'
    };
    return icons[action] || 'info-circle';
}

function formatActionName(action) {
    return action.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase());
}

function updateGamesBySport(gamesBySport) {
    const container = document.getElementById('games-by-sport-chart');
    if (!container) return;
    
    if (gamesBySport.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">No games data</div>';
        return;
    }
    
    container.innerHTML = gamesBySport.slice(0, 5).map(sport => `
        <div class="d-flex justify-content-between align-items-center mb-2">
            <span>${sport.sport}</span>
            <div>
                <span class="badge bg-primary">${sport.count}</span>
            </div>
        </div>
    `).join('');
}

// ======================================
// GAMES MANAGEMENT
// ======================================

async function loadGames() {
    try {
        showLoading(true);
        const data = await fetchAPI('/api/games');
        
        if (data.success) {
            updateGamesTable(data.games);
        } else {
            showNotification('Failed to load games', 'error');
        }
    } catch (error) {
        console.error('Error loading games:', error);
        showNotification('Error loading games', 'error');
    } finally {
        showLoading(false);
    }
}

function updateGamesTable(games) {
    const tbody = document.getElementById('games-table-body');
    if (!tbody) return;
    
    if (games.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No games found</td></tr>';
        return;
    }
    
    tbody.innerHTML = games.map(game => `
        <tr>
            <td>${formatDate(game.date)}</td>
            <td>${formatTime(game.time)}</td>
            <td>
                <div><strong>${game.home_team}</strong> vs <strong>${game.away_team}</strong></div>
                ${game.league ? `<small class="text-muted">${game.league}${game.level ? ' - ' + game.level : ''}</small>` : ''}
            </td>
            <td>${game.location}</td>
            <td><span class="badge bg-secondary">${game.sport}</span></td>
            <td>${game.officials_needed || 1}</td>
            <td>${getStatusBadge(game.status || 'scheduled')}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-outline-primary btn-sm" onclick="editItem(${game.id}, 'game')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="deleteItem(${game.id}, 'game')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

async function applyGamesFilter() {
    const dateFrom = document.getElementById('games-date-from')?.value;
    const dateTo = document.getElementById('games-date-to')?.value;
    const sport = document.getElementById('games-sport-filter')?.value;
    const league = document.getElementById('games-league-filter')?.value;
    
    const params = new URLSearchParams();
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    if (sport) params.append('sport', sport);
    if (league) params.append('league', league);
    
    try {
        showLoading(true);
        const data = await fetchAPI(`/api/games?${params}`);
        
        if (data.success) {
            updateGamesTable(data.games);
        } else {
            showNotification('Failed to filter games', 'error');
        }
    } catch (error) {
        console.error('Error filtering games:', error);
        showNotification('Error filtering games', 'error');
    } finally {
        showLoading(false);
    }
}

async function createGame() {
    const form = document.getElementById('createGameForm');
    if (!form) return;
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // Validation
    if (!data.date || !data.time || !data.home_team || !data.away_team || !data.location || !data.sport) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }
    
    try {
        showLoading(true);
        const result = await fetchAPI('/api/games', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            showNotification('Game created successfully!', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('createGameModal'));
            if (modal) modal.hide();
            form.reset();
            loadGames();
        } else {
            showNotification(result.error || 'Failed to create game', 'error');
        }
    } catch (error) {
        console.error('Create game error:', error);
        showNotification('Error creating game', 'error');
    } finally {
        showLoading(false);
    }
}

// ======================================
// OFFICIALS MANAGEMENT
// ======================================

async function loadOfficials() {
    try {
        showLoading(true);
        const data = await fetchAPI('/api/officials');
        
        if (data.success) {
            updateOfficialsTable(data.officials);
        } else {
            showNotification('Failed to load officials', 'error');
        }
    } catch (error) {
        console.error('Error loading officials:', error);
        showNotification('Error loading officials', 'error');
    } finally {
        showLoading(false);
    }
}

function updateOfficialsTable(officials) {
    const tbody = document.getElementById('officials-table-body');
    if (!tbody) return;
    
    if (officials.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No officials found</td></tr>';
        return;
    }
    
    tbody.innerHTML = officials.map(official => `
        <tr>
            <td>
                <div class="fw-semibold">${official.name}</div>
                ${official.certifications ? `<small class="text-muted">${official.certifications}</small>` : ''}
            </td>
            <td>${official.email || '-'}</td>
            <td>${official.phone || '-'}</td>
            <td>
                <span class="badge bg-info">${official.experience_level || 'Not Set'}</span>
            </td>
            <td>
                <div class="d-flex align-items-center">
                    <span class="me-2">${(official.rating || 0).toFixed(1)}</span>
                    ${generateStarRating(official.rating || 0)}
                </div>
            </td>
            <td>
                <span class="badge bg-secondary">${official.total_assignments || 0}</span>
            </td>
            <td>${getStatusBadge(official.is_active ? 'active' : 'inactive')}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-outline-info btn-sm" onclick="viewOfficialDetails(${official.id})" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-outline-primary btn-sm" onclick="editItem(${official.id}, 'official')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="deleteItem(${official.id}, 'official')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

async function applyOfficialsFilter() {
    const search = document.getElementById('officials-search')?.value;
    const experienceLevel = document.getElementById('officials-experience-filter')?.value;
    
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (experienceLevel) params.append('experience_level', experienceLevel);
    
    try {
        showLoading(true);
        const data = await fetchAPI(`/api/officials?${params}`);
        
        if (data.success) {
            updateOfficialsTable(data.officials);
        } else {
            showNotification('Failed to filter officials', 'error');
        }
    } catch (error) {
        console.error('Error filtering officials:', error);
        showNotification('Error filtering officials', 'error');
    } finally {
        showLoading(false);
    }
}

async function createOfficial() {
    const form = document.getElementById('createOfficialForm');
    if (!form) return;
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // Validation
    if (!data.name || !data.email) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }
    
    try {
        showLoading(true);
        const result = await fetchAPI('/api/officials', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            showNotification('Official created successfully!', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('createOfficialModal'));
            if (modal) modal.hide();
            form.reset();
            loadOfficials();
        } else {
            showNotification(result.error || 'Failed to create official', 'error');
        }
    } catch (error) {
        console.error('Create official error:', error);
        showNotification('Error creating official', 'error');
    } finally {
        showLoading(false);
    }
}

async function viewOfficialDetails(officialId) {
    try {
        const data = await fetchAPI(`/api/officials/${officialId}`);
        
        if (data.success) {
            showOfficialDetailsModal(data.official, data.recent_assignments || []);
        } else {
            showNotification('Failed to load official details', 'error');
        }
    } catch (error) {
        console.error('Error loading official details:', error);
        showNotification('Error loading official details', 'error');
    }
}

function showOfficialDetailsModal(official, recentAssignments) {
    // Create and show official details modal
    const modalContent = `
        <div class="modal fade" id="officialDetailsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="fas fa-user-tie me-2"></i>${official.name}</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Contact Information</h6>
                                <p><strong>Email:</strong> ${official.email || 'N/A'}</p>
                                <p><strong>Phone:</strong> ${official.phone || 'N/A'}</p>
                                <p><strong>Experience:</strong> ${official.experience_level || 'Not specified'}</p>
                            </div>
                            <div class="col-md-6">
                                <h6>Official Information</h6>
                                <p><strong>Certifications:</strong> ${official.certifications || 'None listed'}</p>
                                <p><strong>Rating:</strong> ${generateStarRating(official.rating)} (${(official.rating || 0).toFixed(1)})</p>
                                <p><strong>Total Assignments:</strong> ${official.total_assignments || 0}</p>
                            </div>
                        </div>
                        <div class="row mt-3">
                            <div class="col-12">
                                <h6>Recent Assignments</h6>
                                ${recentAssignments.length > 0 ? `
                                    <div class="table-responsive">
                                        <table class="table table-sm">
                                            <thead>
                                                <tr>
                                                    <th>Date</th>
                                                    <th>Game</th>
                                                    <th>Position</th>
                                                    <th>Status</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                ${recentAssignments.map(assignment => `
                                                    <tr>
                                                        <td>${formatDate(assignment.date)}</td>
                                                        <td>${assignment.home_team} vs ${assignment.away_team}</td>
                                                        <td>${assignment.position || 'Official'}</td>
                                                        <td>${getStatusBadge(assignment.status)}</td>
                                                    </tr>
                                                `).join('')}
                                            </tbody>
                                        </table>
                                    </div>
                                ` : '<p class="text-muted">No recent assignments</p>'}
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('officialDetailsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to DOM
    document.body.insertAdjacentHTML('beforeend', modalContent);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('officialDetailsModal'));
    modal.show();
    
    // Clean up on close
    document.getElementById('officialDetailsModal').addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
}

// ======================================
// ASSIGNMENTS MANAGEMENT
// ======================================

async function loadAssignments() {
    try {
        showLoading(true);
        const data = await fetchAPI('/api/assignments');
        
        if (data.success) {
            updateAssignmentsTable(data.assignments);
        } else {
            showNotification('Failed to load assignments', 'error');
        }
    } catch (error) {
        console.error('Error loading assignments:', error);
        showNotification('Error loading assignments', 'error');
    } finally {
        showLoading(false);
    }
}

function updateAssignmentsTable(assignments) {
    const tbody = document.getElementById('assignments-table-body');
    if (!tbody) return;
    
    if (assignments.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No assignments found</td></tr>';
        return;
    }
    
    tbody.innerHTML = assignments.map(assignment => `
        <tr>
            <td>
                <div>${formatDate(assignment.date)} ${formatTime(assignment.time)}</div>
                <small class="text-muted">${assignment.sport}</small>
            </td>
            <td>
                <div><strong>${assignment.home_team}</strong> vs <strong>${assignment.away_team}</strong></div>
                <small class="text-muted">${assignment.location}</small>
            </td>
            <td>
                <div class="fw-semibold">${assignment.official_name}</div>
                <small class="text-muted">${assignment.official_email || ''}</small>
            </td>
            <td><span class="badge bg-info">${assignment.position || 'Official'}</span></td>
            <td>${getStatusBadge(assignment.status)}</td>
            <td>${formatDate(assignment.assigned_date)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-outline-primary btn-sm" onclick="editItem(${assignment.id}, 'assignment')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="deleteItem(${assignment.id}, 'assignment')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

async function applyAssignmentsFilter() {
    const status = document.getElementById('assignments-status-filter')?.value;
    const dateFrom = document.getElementById('assignments-date-from')?.value;
    const dateTo = document.getElementById('assignments-date-to')?.value;
    
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    
    try {
        showLoading(true);
        const data = await fetchAPI(`/api/assignments?${params}`);
        
        if (data.success) {
            updateAssignmentsTable(data.assignments);
        } else {
            showNotification('Failed to filter assignments', 'error');
        }
    } catch (error) {
        console.error('Error filtering assignments:', error);
        showNotification('Error filtering assignments', 'error');
    } finally {
        showLoading(false);
    }
}

async function createAssignment() {
    const form = document.getElementById('createAssignmentForm');
    if (!form) return;
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // Validation
    if (!data.game_id || !data.official_id) {
        showNotification('Please select both a game and an official', 'error');
        return;
    }
    
    try {
        showLoading(true);
        const result = await fetchAPI('/api/assignments', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            showNotification('Assignment created successfully!', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('createAssignmentModal'));
            if (modal) modal.hide();
            form.reset();
            loadAssignments();
        } else {
            showNotification(result.error || 'Failed to create assignment', 'error');
        }
    } catch (error) {
        console.error('Create assignment error:', error);
        showNotification('Error creating assignment', 'error');
    } finally {
        showLoading(false);
    }
}

// ======================================
// LOCATIONS MANAGEMENT
// ======================================

async function loadLocations() {
    try {
        showLoading(true);
        const data = await fetchAPI('/api/locations');
        
        if (data.success) {
            updateLocationsTable(data.locations);
        } else {
            showNotification('Failed to load locations', 'error');
        }
    } catch (error) {
        console.error('Error loading locations:', error);
        showNotification('Error loading locations', 'error');
    } finally {
        showLoading(false);
    }
}

function updateLocationsTable(locations) {
    const tbody = document.getElementById('locations-table-body');
    if (!tbody) return;
    
    if (locations.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No locations found</td></tr>';
        return;
    }
    
    tbody.innerHTML = locations.map(location => `
        <tr>
            <td>
                <div class="fw-semibold">${location.name}</div>
            </td>
            <td>${location.address || '-'}</td>
            <td>${location.city || '-'}</td>
            <td>${location.state || '-'}</td>
            <td>${location.capacity || 0}</td>
            <td>
                ${location.contact_person ? `<div>${location.contact_person}</div>` : ''}
                ${location.phone ? `<small class="text-muted">${location.phone}</small>` : ''}
            </td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-outline-primary btn-sm" onclick="editItem(${location.id}, 'location')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="deleteItem(${location.id}, 'location')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

async function applyLocationsFilter() {
    const search = document.getElementById('locations-search')?.value;
    
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    
    try {
        showLoading(true);
        const data = await fetchAPI(`/api/locations?${params}`);
        
        if (data.success) {
            updateLocationsTable(data.locations);
        } else {
            showNotification('Failed to filter locations', 'error');
        }
    } catch (error) {
        console.error('Error filtering locations:', error);
        showNotification('Error filtering locations', 'error');
    } finally {
        showLoading(false);
    }
}

async function createLocation() {
    const form = document.getElementById('createLocationForm');
    if (!form) return;
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // Validation
    if (!data.name) {
        showNotification('Please enter a location name', 'error');
        return;
    }
    
    try {
        showLoading(true);
        const result = await fetchAPI('/api/locations', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            showNotification('Location created successfully!', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('createLocationModal'));
            if (modal) modal.hide();
            form.reset();
            loadLocations();
        } else {
            showNotification(result.error || 'Failed to create location', 'error');
        }
    } catch (error) {
        console.error('Create location error:', error);
        showNotification('Error creating location', 'error');
    } finally {
        showLoading(false);
    }
}

// ======================================
// USERS MANAGEMENT
// ======================================

async function loadUsers() {
    try {
        showLoading(true);
        const data = await fetchAPI('/api/users');
        
        if (data.success) {
            updateUsersTable(data.users);
        } else {
            showNotification('Failed to load users', 'error');
        }
    } catch (error) {
        console.error('Error loading users:', error);
        showNotification('Error loading users', 'error');
    } finally {
        showLoading(false);
    }
}

function updateUsersTable(users) {
    const tbody = document.getElementById('users-table-body');
    if (!tbody) return;
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No users found</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>
                <div class="fw-semibold">${user.username}</div>
            </td>
            <td>${user.full_name}</td>
            <td>${user.email || '-'}</td>
            <td>
                <span class="badge bg-${getRoleBadgeColor(user.role)}">${user.role.charAt(0).toUpperCase() + user.role.slice(1)}</span>
            </td>
            <td>${getStatusBadge(user.is_active ? 'active' : 'inactive')}</td>
            <td>${user.last_login ? formatDateTime(user.last_login) : 'Never'}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-outline-primary btn-sm" onclick="editItem(${user.id}, 'user')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="deleteItem(${user.id}, 'user')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function getRoleBadgeColor(role) {
    const colors = {
        'user': 'secondary',
        'official': 'info',
        'admin': 'warning',
        'superadmin': 'danger'
    };
    return colors[role] || 'secondary';
}

async function applyUsersFilter() {
    const search = document.getElementById('users-search')?.value;
    const role = document.getElementById('users-role-filter')?.value;
    
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (role) params.append('role', role);
    
    try {
        showLoading(true);
        const data = await fetchAPI(`/api/users?${params}`);
        
        if (data.success) {
            updateUsersTable(data.users);
        } else {
            showNotification('Failed to filter users', 'error');
        }
    } catch (error) {
        console.error('Error filtering users:', error);
        showNotification('Error filtering users', 'error');
    } finally {
        showLoading(false);
    }
}

async function createUser() {
    const form = document.getElementById('createUserForm');
    if (!form) return;
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // Validation
    if (!data.username || !data.full_name || !data.email || !data.role || !data.password) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }
    
    try {
        showLoading(true);
        const result = await fetchAPI('/api/users', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            showNotification('User created successfully!', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('createUserModal'));
            if (modal) modal.hide();
            form.reset();
            loadUsers();
        } else {
            showNotification(result.error || 'Failed to create user', 'error');
        }
    } catch (error) {
        console.error('Create user error:', error);
        showNotification('Error creating user', 'error');
    } finally {
        showLoading(false);
    }
}

// ======================================
// REPORTS AND ANALYTICS
// ======================================

async function loadReports() {
    try {
        showLoading(true);
        const data = await fetchAPI('/api/reports/stats');
        
        if (data.success) {
            updateReportsContent(data.stats);
        } else {
            showNotification('Failed to load reports', 'error');
        }
    } catch (error) {
        console.error('Error loading reports:', error);
        showNotification('Error loading reports', 'error');
    } finally {
        showLoading(false);
    }
}

function updateReportsContent(stats) {
    const container = document.getElementById('reports-content');
    if (!container) return;
    
    container.innerHTML = `
        <div class="row g-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Games by Status</h6>
                    </div>
                    <div class="card-body">
                        ${(stats.games_by_status || []).map(item => `
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span>${item.status.charAt(0).toUpperCase() + item.status.slice(1)}</span>
                                <span class="badge bg-primary">${item.count}</span>
                            </div>
                        `).join('')}
                        ${stats.games_by_status?.length === 0 ? '<div class="text-center text-muted">No data available</div>' : ''}
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Assignments by Status</h6>
                    </div>
                    <div class="card-body">
                        ${(stats.assignments_by_status || []).map(item => `
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span>${item.status.charAt(0).toUpperCase() + item.status.slice(1)}</span>
                                <span class="badge bg-success">${item.count}</span>
                            </div>
                        `).join('')}
                        ${stats.assignments_by_status?.length === 0 ? '<div class="text-center text-muted">No data available</div>' : ''}
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row g-4 mt-3">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Officials by Experience</h6>
                    </div>
                    <div class="card-body">
                        ${(stats.officials_by_experience || []).map(item => `
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span>${item.experience_level}</span>
                                <span class="badge bg-info">${item.count}</span>
                            </div>
                        `).join('')}
                        ${stats.officials_by_experience?.length === 0 ? '<div class="text-center text-muted">No data available</div>' : ''}
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Top Officials</h6>
                    </div>
                    <div class="card-body">
                        ${(stats.top_officials || []).slice(0, 5).map(official => `
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <div>
                                    <div class="fw-semibold">${official.name}</div>
                                    <small class="text-muted">Rating: ${(official.avg_rating || 0).toFixed(1)}</small>
                                </div>
                                <span class="badge bg-warning">${official.assignment_count} assignments</span>
                            </div>
                        `).join('')}
                        ${stats.top_officials?.length === 0 ? '<div class="text-center text-muted">No data available</div>' : ''}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function generateReport(type) {
    showNotification(`Generating ${type} report...`, 'info');
    // This would typically open a detailed report modal or navigate to a report page
    loadReports();
}

// ======================================
// MODAL AND CRUD OPERATIONS
// ======================================

function openCreateModal(type) {
    const modalId = `create${type.charAt(0).toUpperCase() + type.slice(1)}Modal`;
    const modal = new bootstrap.Modal(document.getElementById(modalId));
    if (modal) {
        modal.show();
    }
}

async function editItem(id, type) {
    currentEditId = id;
    currentEditType = type;
    
    try {
        showLoading(true);
        const data = await fetchAPI(`/api/${type}s/${id}`);
        
        if (data.success) {
            const item = data[type] || data.user || data.game || data.official || data.assignment || data.location;
            populateEditModal(item, type);
            const modal = new bootstrap.Modal(document.getElementById('editModal'));
            modal.show();
        } else {
            showNotification(`Failed to load ${type} for editing`, 'error');
        }
    } catch (error) {
        console.error(`Edit ${type} error:`, error);
        showNotification(`Error loading ${type} for editing`, 'error');
    } finally {
        showLoading(false);
    }
}

function populateEditModal(item, type) {
    const title = document.getElementById('editModalTitle');
    const body = document.getElementById('editModalBody');
    
    if (title) {
        title.innerHTML = `<i class="fas fa-edit me-2"></i>Edit ${type.charAt(0).toUpperCase() + type.slice(1)}`;
    }
    
    if (body) {
        body.innerHTML = generateEditForm(item, type);
    }
}

function generateEditForm(item, type) {
    switch(type) {
        case 'game':
            return generateGameEditForm(item);
        case 'official':
            return generateOfficialEditForm(item);
        case 'assignment':
            return generateAssignmentEditForm(item);
        case 'user':
            return generateUserEditForm(item);
        case 'location':
            return generateLocationEditForm(item);
        default:
            return '<p>Edit form not available for this item type.</p>';
    }
}

function generateGameEditForm(game) {
    return `
        <form id="editForm">
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label">Date *</label>
                    <input type="date" class="form-control" name="date" value="${game.date}" required>
                </div>
                <div class="col-md-6 mb-3">
                    <label class="form-label">Time *</label>
                    <input type="time" class="form-control" name="time" value="${game.time}" required>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label">Home Team *</label>
                    <input type="text" class="form-control" name="home_team" value="${game.home_team}" required>
                </div>
                <div class="col-md-6 mb-3">
                    <label class="form-label">Away Team *</label>
                    <input type="text" class="form-control" name="away_team" value="${game.away_team}" required>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label">Location *</label>
                    <input type="text" class="form-control" name="location" value="${game.location}" required>
                </div>
                <div class="col-md-6 mb-3">
                    <label class="form-label">Sport *</label>
                    <input type="text" class="form-control" name="sport" value="${game.sport}" required>
                </div>
            </div>
            <div class="row">
                <div class="col-md-4 mb-3">
                    <label class="form-label">League</label>
                    <input type="text" class="form-control" name="league" value="${game.league || ''}">
                </div>
                <div class="col-md-4 mb-3">
                    <label class="form-label">Level</label>
                    <input type="text" class="form-control" name="level" value="${game.level || ''}">
                </div>
                <div class="col-md-4 mb-3">
                    <label class="form-label">Officials Needed</label>
                    <input type="number" class="form-control" name="officials_needed" value="${game.officials_needed || 1}" min="1">
                </div>
            </div>
            <div class="mb-3">
                <label class="form-label">Notes</label>
                <textarea class="form-control" name="notes" rows="3">${game.notes || ''}</textarea>
            </div>
        </form>
    `;
}

function generateOfficialEditForm(official) {
    return `
        <form id="editForm">
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label">Name *</label>
                    <input type="text" class="form-control" name="name" value="${official.name}" required>
                </div>
                <div class="col-md-6 mb-3">
                    <label class="form-label">Email *</label>
                    <input type="email" class="form-control" name="email" value="${official.email}" required>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label">Phone</label>
                    <input type="tel" class="form-control" name="phone" value="${location.phone || ''}">
                </div>
            </div>
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label">Email</label>
                    <input type="email" class="form-control" name="email" value="${location.email || ''}">
                </div>
                <div class="col-md-6 mb-3">
                    <label class="form-label">Capacity</label>
                    <input type="number" class="form-control" name="capacity" value="${location.capacity || 0}" min="0">
                </div>
            </div>
            <div class="mb-3">
                <label class="form-label">Notes</label>
                <textarea class="form-control" name="notes" rows="3">${location.notes || ''}</textarea>
            </div>
        </form>
    `;
}

async function saveEdit() {
    if (!currentEditId || !currentEditType) {
        showNotification('Edit session invalid', 'error');
        return;
    }
    
    const form = document.getElementById('editForm');
    if (!form) {
        showNotification('Edit form not found', 'error');
        return;
    }
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // Handle checkbox for is_active
    if (currentEditType === 'user') {
        data.is_active = formData.has('is_active') ? 1 : 0;
    }
    
    try {
        showLoading(true);
        const result = await fetchAPI(`/api/${currentEditType}s/${currentEditId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            showNotification(`${currentEditType.charAt(0).toUpperCase() + currentEditType.slice(1)} updated successfully!`, 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('editModal'));
            if (modal) modal.hide();
            refreshCurrentSection();
        } else {
            showNotification(result.error || `Failed to update ${currentEditType}`, 'error');
        }
    } catch (error) {
        console.error(`Update ${currentEditType} error:`, error);
        showNotification(`Error updating ${currentEditType}`, 'error');
    } finally {
        showLoading(false);
        currentEditId = null;
        currentEditType = null;
    }
}

async function deleteItem(id, type) {
    const itemName = type.charAt(0).toUpperCase() + type.slice(1);
    
    if (!confirm(`Are you sure you want to delete this ${type}? This action cannot be undone.`)) {
        return;
    }
    
    try {
        showLoading(true);
        const result = await fetchAPI(`/api/${type}s/${id}`, {
            method: 'DELETE'
        });
        
        if (result.success) {
            showNotification(`${itemName} deleted successfully!`, 'success');
            refreshCurrentSection();
        } else {
            showNotification(result.error || `Failed to delete ${type}`, 'error');
        }
    } catch (error) {
        console.error(`Delete ${type} error:`, error);
        showNotification(`Error deleting ${type}`, 'error');
    } finally {
        showLoading(false);
    }
}

// ======================================
// EXPORT FUNCTIONS
// ======================================

async function exportData(type) {
    try {
        showLoading(true);
        showNotification(`Preparing ${type} export...`, 'info');
        
        const response = await fetch(`/api/export/${type}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `${type}_export_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showNotification(`${type.charAt(0).toUpperCase() + type.slice(1)} exported successfully!`, 'success');
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Export failed');
        }
    } catch (error) {
        console.error(`Export ${type} error:`, error);
        showNotification(`Error exporting ${type}: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// ======================================
// FORM HANDLING
// ======================================

function handleFormSubmit(event) {
    // Prevent default form submission for forms with specific classes
    if (event.target.classList.contains('ajax-form')) {
        event.preventDefault();
        // Handle AJAX form submission
    }
}

function handleModalClosed(event) {
    // Reset form data when modals are closed
    const modal = event.target;
    const forms = modal.querySelectorAll('form');
    forms.forEach(form => {
        if (form.id !== 'editForm') { // Don't reset edit forms automatically
            form.reset();
        }
    });
    
    // Clear edit state
    if (modal.id === 'editModal') {
        currentEditId = null;
        currentEditType = null;
    }
}

function handleWindowResize() {
    // Handle responsive design adjustments
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (window.innerWidth < 768) {
        // Mobile view adjustments
        if (sidebar && !sidebar.classList.contains('mobile-adjusted')) {
            sidebar.classList.add('mobile-adjusted');
        }
    } else {
        // Desktop view adjustments
        if (sidebar && sidebar.classList.contains('mobile-adjusted')) {
            sidebar.classList.remove('mobile-adjusted');
        }
    }
}

function handleKeyboardShortcuts(event) {
    // Keyboard shortcuts for better user experience
    if (event.ctrlKey || event.metaKey) {
        switch(event.key) {
            case 'n':
                event.preventDefault();
                // Open new item modal based on current section
                if (currentSection && currentSection !== 'dashboard' && currentSection !== 'reports') {
                    openCreateModal(currentSection.slice(0, -1)); // Remove 's' from section name
                }
                break;
            case 'r':
                event.preventDefault();
                // Refresh current section
                refreshCurrentSection();
                break;
            case 'e':
                event.preventDefault();
                // Export current section data
                if (currentSection && ['games', 'officials', 'assignments'].includes(currentSection)) {
                    exportData(currentSection);
                }
                break;
        }
    }
    
    // Escape key handling
    if (event.key === 'Escape') {
        // Close any open modals
        const openModals = document.querySelectorAll('.modal.show');
        openModals.forEach(modal => {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        });
    }
}

// ======================================
// UI INITIALIZATION FUNCTIONS
// ======================================

function initializeModals() {
    // Initialize all Bootstrap modals
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        new bootstrap.Modal(modal, {
            keyboard: true,
            backdrop: true
        });
    });
}

function initializeTooltips() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function setupMobileHandlers() {
    // Set up mobile-specific event handlers
    const menuButton = document.querySelector('[onclick="toggleSidebar()"]');
    if (menuButton) {
        menuButton.addEventListener('click', function(e) {
            e.preventDefault();
            toggleSidebar();
        });
    }
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(event) {
        if (window.innerWidth < 768) {
            const sidebar = document.querySelector('.sidebar');
            const menuButton = document.querySelector('[onclick="toggleSidebar()"]');
            
            if (sidebar && sidebar.classList.contains('show') && 
                !sidebar.contains(event.target) && 
                !menuButton.contains(event.target)) {
                sidebar.classList.remove('show');
            }
        }
    });
}

// ======================================
// SEARCH AND FILTERING FUNCTIONS
// ======================================

function setupGlobalSearch() {
    const searchInput = document.getElementById('global-search');
    if (searchInput) {
        const debouncedSearch = debounce(performGlobalSearch, 300);
        searchInput.addEventListener('input', debouncedSearch);
    }
}

async function performGlobalSearch(event) {
    const query = event.target.value.trim();
    
    if (query.length < 2) {
        hideSearchResults();
        return;
    }
    
    try {
        const data = await fetchAPI(`/api/search?q=${encodeURIComponent(query)}`);
        
        if (data.success) {
            displaySearchResults(data.results);
        }
    } catch (error) {
        console.error('Global search error:', error);
    }
}

function displaySearchResults(results) {
    // Implementation for displaying global search results
    console.log('Search results:', results);
}

function hideSearchResults() {
    const resultsContainer = document.getElementById('search-results');
    if (resultsContainer) {
        resultsContainer.style.display = 'none';
    }
}

// ======================================
// VALIDATION FUNCTIONS
// ======================================

function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    const errors = [];
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            errors.push(`${field.name || field.id} is required`);
            field.classList.add('is-invalid');
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    // Email validation
    const emailFields = form.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
        if (field.value && !isValidEmail(field.value)) {
            isValid = false;
            errors.push('Please enter a valid email address');
            field.classList.add('is-invalid');
        }
    });
    
    // Phone validation
    const phoneFields = form.querySelectorAll('input[type="tel"]');
    phoneFields.forEach(field => {
        if (field.value && !isValidPhone(field.value)) {
            isValid = false;
            errors.push('Please enter a valid phone number');
            field.classList.add('is-invalid');
        }
    });
    
    if (!isValid) {
        showNotification(errors.join(', '), 'error');
    }
    
    return isValid;
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function isValidPhone(phone) {
    const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
    return phoneRegex.test(phone.replace(/[-\s\(\)]/g, ''));
}

// ======================================
// PERFORMANCE OPTIMIZATION
// ======================================

function optimizeTableRendering(data, tableId, renderFunction) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    // Virtual scrolling for large datasets
    if (data.length > 100) {
        implementVirtualScrolling(table, data, renderFunction);
    } else {
        renderFunction(data);
    }
}

function implementVirtualScrolling(table, data, renderFunction) {
    // Basic virtual scrolling implementation
    const itemsPerPage = 50;
    let currentPage = 0;
    
    function renderPage(page) {
        const start = page * itemsPerPage;
        const end = start + itemsPerPage;
        const pageData = data.slice(start, end);
        renderFunction(pageData);
    }
    
    renderPage(currentPage);
    
    // Add pagination controls
    addPaginationControls(table, data.length, itemsPerPage, renderPage);
}

function addPaginationControls(table, totalItems, itemsPerPage, renderPageFunction) {
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    let currentPage = 0;
    
    const paginationContainer = document.createElement('div');
    paginationContainer.className = 'pagination-container mt-3';
    
    const pagination = document.createElement('nav');
    pagination.innerHTML = `
        <ul class="pagination justify-content-center">
            <li class="page-item" id="prev-page">
                <a class="page-link" href="#">Previous</a>
            </li>
            <li class="page-item active" id="page-info">
                <span class="page-link">Page 1 of ${totalPages}</span>
            </li>
            <li class="page-item" id="next-page">
                <a class="page-link" href="#">Next</a>
            </li>
        </ul>
    `;
    
    paginationContainer.appendChild(pagination);
    table.parentNode.appendChild(paginationContainer);
    
    // Event handlers
    document.getElementById('prev-page').addEventListener('click', function(e) {
        e.preventDefault();
        if (currentPage > 0) {
            currentPage--;
            renderPageFunction(currentPage);
            updatePaginationUI();
        }
    });
    
    document.getElementById('next-page').addEventListener('click', function(e) {
        e.preventDefault();
        if (currentPage < totalPages - 1) {
            currentPage++;
            renderPageFunction(currentPage);
            updatePaginationUI();
        }
    });
    
    function updatePaginationUI() {
        document.getElementById('page-info').innerHTML = `
            <span class="page-link">Page ${currentPage + 1} of ${totalPages}</span>
        `;
        
        document.getElementById('prev-page').classList.toggle('disabled', currentPage === 0);
        document.getElementById('next-page').classList.toggle('disabled', currentPage === totalPages - 1);
    }
    
    updatePaginationUI();
}

// ======================================
// ERROR HANDLING AND LOGGING
// ======================================

function setupErrorHandling() {
    // Global error handler
    window.addEventListener('error', function(event) {
        console.error('Global error:', event.error);
        logError('JavaScript Error', event.error.message, event.filename, event.lineno);
    });
    
    // Unhandled promise rejection handler
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled promise rejection:', event.reason);
        logError('Promise Rejection', event.reason.message || event.reason);
    });
}

function logError(type, message, filename = '', line = '') {
    // Log error to console and potentially send to server
    const errorData = {
        type: type,
        message: message,
        filename: filename,
        line: line,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href
    };
    
    console.error('Error logged:', errorData);
    
    // Optionally send to server for logging
    // fetch('/api/log-error', {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify(errorData)
    // }).catch(err => console.error('Failed to log error to server:', err));
}

// ======================================
// ACCESSIBILITY FUNCTIONS
// ======================================

function enhanceAccessibility() {
    // Add ARIA labels and roles
    addAriaLabels();
    
    // Keyboard navigation enhancement
    enhanceKeyboardNavigation();
    
    // Screen reader announcements
    setupScreenReaderAnnouncements();
}

function addAriaLabels() {
    // Add missing ARIA labels to interactive elements
    const buttons = document.querySelectorAll('button:not([aria-label])');
    buttons.forEach(button => {
        if (button.title) {
            button.setAttribute('aria-label', button.title);
        }
    });
    
    // Add roles to navigation elements
    const navElements = document.querySelectorAll('.nav-link');
    navElements.forEach(nav => {
        nav.setAttribute('role', 'menuitem');
    });
}

function enhanceKeyboardNavigation() {
    // Ensure all interactive elements are keyboard accessible
    const interactiveElements = document.querySelectorAll('button, a, input, select, textarea');
    interactiveElements.forEach(element => {
        if (!element.tabIndex && element.tabIndex !== 0) {
            element.tabIndex = 0;
        }
    });
}

function setupScreenReaderAnnouncements() {
    // Create live region for screen reader announcements
    const liveRegion = document.createElement('div');
    liveRegion.id = 'sr-live-region';
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.style.position = 'absolute';
    liveRegion.style.left = '-10000px';
    liveRegion.style.width = '1px';
    liveRegion.style.height = '1px';
    liveRegion.style.overflow = 'hidden';
    document.body.appendChild(liveRegion);
}

function announceToScreenReader(message) {
    const liveRegion = document.getElementById('sr-live-region');
    if (liveRegion) {
        liveRegion.textContent = message;
        setTimeout(() => {
            liveRegion.textContent = '';
        }, 1000);
    }
}

// ======================================
// CLEANUP AND MEMORY MANAGEMENT
// ======================================

function cleanup() {
    // Clear intervals
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    // Remove event listeners
    document.removeEventListener('submit', handleFormSubmit);
    document.removeEventListener('hidden.bs.modal', handleModalClosed);
    window.removeEventListener('resize', handleWindowResize);
    document.removeEventListener('keydown', handleKeyboardShortcuts);
    
    // Clear any timeouts
    // (Add specific timeout clearing if needed)
}

// Set up cleanup on page unload
window.addEventListener('beforeunload', cleanup);

// ======================================
// INITIALIZATION COMPLETE
// ======================================

// Initialize error handling and accessibility when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    setupErrorHandling();
    enhanceAccessibility();
    setupGlobalSearch();
});

console.log('✅ Sports Schedulers - Main JavaScript loaded successfully');
console.log('🔧 Phase 4 Complete: Full CRUD Operations, Real-time Updates, Professional UI');
console.log('📱 Features: Responsive Design, Error Handling, Accessibility, Performance Optimization');</label>
                    <input type="tel" class="form-control" name="phone" value="${official.phone || ''}">
                </div>
                <div class="col-md-6 mb-3">
                    <label class="form-label">Experience Level</label>
                    <select class="form-select" name="experience_level">
                        <option value="Beginner" ${official.experience_level === 'Beginner' ? 'selected' : ''}>Beginner</option>
                        <option value="Intermediate" ${official.experience_level === 'Intermediate' ? 'selected' : ''}>Intermediate</option>
                        <option value="Advanced" ${official.experience_level === 'Advanced' ? 'selected' : ''}>Advanced</option>
                        <option value="Expert" ${official.experience_level === 'Expert' ? 'selected' : ''}>Expert</option>
                    </select>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label">Certifications</label>
                    <input type="text" class="form-control" name="certifications" value="${official.certifications || ''}">
                </div>
                <div class="col-md-6 mb-3">
                    <label class="form-label">Rating</label>
                    <input type="number" class="form-control" name="rating" value="${official.rating || 0}" min="0" max="5" step="0.1">
                </div>
            </div>
            <div class="mb-3">
                <label class="form-label">Availability</label>
                <select class="form-select" name="availability">
                    <option value="Flexible" ${official.availability === 'Flexible' ? 'selected' : ''}>Flexible</option>
                    <option value="Weekends Only" ${official.availability === 'Weekends Only' ? 'selected' : ''}>Weekends Only</option>
                    <option value="Evenings" ${official.availability === 'Evenings' ? 'selected' : ''}>Evenings</option>
                    <option value="Limited" ${official.availability === 'Limited' ? 'selected' : ''}>Limited</option>
                </select>
            </div>
        </form>
    `;
}

function generateAssignmentEditForm(assignment) {
    return `
        <form id="editForm">
            <div class="mb-3">
                <label class="form-label">Position</label>
                <select class="form-select" name="position">
                    <option value="Official" ${assignment.position === 'Official' ? 'selected' : ''}>Official</option>
                    <option value="Referee" ${assignment.position === 'Referee' ? 'selected' : ''}>Referee</option>
                    <option value="Umpire" ${assignment.position === 'Umpire' ? 'selected' : ''}>Umpire</option>
                    <option value="Crew Chief" ${assignment.position === 'Crew Chief' ? 'selected' : ''}>Crew Chief</option>
                    <option value="Line Judge" ${assignment.position === 'Line Judge' ? 'selected' : ''}>Line Judge</option>
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Status</label>
                <select class="form-select" name="status">
                    <option value="pending" ${assignment.status === 'pending' ? 'selected' : ''}>Pending</option>
                    <option value="confirmed" ${assignment.status === 'confirmed' ? 'selected' : ''}>Confirmed</option>
                    <option value="declined" ${assignment.status === 'declined' ? 'selected' : ''}>Declined</option>
                    <option value="completed" ${assignment.status === 'completed' ? 'selected' : ''}>Completed</option>
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Notes</label>
                <textarea class="form-control" name="notes" rows="3">${assignment.notes || ''}</textarea>
            </div>
        </form>
    `;
}

function generateUserEditForm(user) {
    return `
        <form id="editForm">
            <div class="mb-3">
                <label class="form-label">Username *</label>
                <input type="text" class="form-control" name="username" value="${user.username}" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Full Name *</label>
                <input type="text" class="form-control" name="full_name" value="${user.full_name}" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Email *</label>
                <input type="email" class="form-control" name="email" value="${user.email}" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Phone</label>
                <input type="tel" class="form-control" name="phone" value="${user.phone || ''}">
            </div>
            <div class="mb-3">
                <label class="form-label">New Password (leave blank to keep current)</label>
                <input type="password" class="form-control" name="password">
            </div>
            <div class="mb-3">
                <label class="form-label">Role *</label>
                <select class="form-select" name="role" required>
                    <option value="user" ${user.role === 'user' ? 'selected' : ''}>User</option>
                    <option value="official" ${user.role === 'official' ? 'selected' : ''}>Official</option>
                    <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>Admin</option>
                    <option value="superadmin" ${user.role === 'superadmin' ? 'selected' : ''}>Super Admin</option>
                </select>
            </div>
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" name="is_active" value="1" ${user.is_active ? 'checked' : ''}>
                    <label class="form-check-label">Active User</label>
                </div>
            </div>
        </form>
    `;
}

function generateLocationEditForm(location) {
    return `
        <form id="editForm">
            <div class="mb-3">
                <label class="form-label">Location Name *</label>
                <input type="text" class="form-control" name="name" value="${location.name}" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Address</label>
                <input type="text" class="form-control" name="address" value="${location.address || ''}">
            </div>
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label">City</label>
                    <input type="text" class="form-control" name="city" value="${location.city || ''}">
                </div>
                <div class="col-md-3 mb-3">
                    <label class="form-label">State</label>
                    <input type="text" class="form-control" name="state" value="${location.state || ''}" maxlength="2">
                </div>
                <div class="col-md-3 mb-3">
                    <label class="form-label">ZIP</label>
                    <input type="text" class="form-control" name="zip_code" value="${location.zip_code || ''}" maxlength="10">
                </div>
            </div>
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label">Contact Person</label>
                    <input type="text" class="form-control" name="contact_person" value="${location.contact_person || ''}">
                </div>
                <div class="col-md-6 mb-3">
                    <label class="form-label">Phone
