// Initialize responsive tables
export function initResponsiveTable(container?: HTMLElement) {
  const tables = container 
    ? container.querySelectorAll('.table-responsive[data-pattern]')
    : document.querySelectorAll('.table-responsive[data-pattern]');
    
  tables.forEach((table) => {
    const pattern = table.getAttribute('data-pattern');
    
    if (pattern === 'priority-columns') {
      // Add mq class to html element for responsive behavior
      if (!document.documentElement.classList.contains('mq')) {
        document.documentElement.classList.add('mq', 'js');
      }
      
      // Initialize focus behavior
      const rows = table.querySelectorAll('tbody tr');
      rows.forEach((row) => {
        row.addEventListener('click', function() {
          // Remove focused class from all rows
          rows.forEach(r => r.classList.remove('focused'));
          // Add focused class to clicked row
          this.classList.add('focused');
        });
      });
    }
  });
}

// Global initialization
declare global {
  interface Window {
    initResponsiveTable: typeof initResponsiveTable;
  }
}

// Make it available globally for the RWD table script
if (typeof window !== 'undefined') {
  window.initResponsiveTable = initResponsiveTable;
}