/**
 * Toggles the display of all zones and fresh zones charts for a given chat and interval.
 * @param {number} chatId - The identifier for the chat session.
 * @param {string} interval - The interval identifier (e.g., '1mo', '1d').
 */
function toggleFreshZones(chatId, interval) {
    var freshToggle = document.getElementById('fresh_toggle_' + chatId + '_' + interval).checked;
    var chartAllZones = document.getElementById('chart_all_zones_' + chatId + '_' + interval);
    var chartFreshZones = document.getElementById('chart_fresh_zones_' + chatId + '_' + interval);
    
    if (freshToggle) {
      chartAllZones.style.display = 'none';
      chartFreshZones.style.display = 'block';
    } else {
      chartAllZones.style.display = 'block';
      chartFreshZones.style.display = 'none';
    }
  }
  
  document.addEventListener("DOMContentLoaded", function() {
    const chatHeadings = document.querySelectorAll(".chat-heading");
    const chatPanels = document.querySelectorAll(".chat-panel");
    const minimizeBtn = document.getElementById("minimizeSidebar");
    const sidebar = document.getElementById("sidebar");
    const mainContent = document.getElementById("mainContent");
  
    /**
     * Toggles the sidebar between minimized and expanded states.
     */
    function toggleSidebar() {
      sidebar.classList.toggle("minimized");
      mainContent.classList.toggle("expanded");
  
      // Change the icon of the minimize button
      const icon = minimizeBtn.querySelector("i");
      if (sidebar.classList.contains("minimized")) {
        icon.classList.remove("fa-chevron-left");
        icon.classList.add("fa-chevron-right");
      } else {
        icon.classList.remove("fa-chevron-right");
        icon.classList.add("fa-chevron-left");
      }
  
      // Save sidebar state in localStorage
      if (sidebar.classList.contains("minimized")) {
        localStorage.setItem("sidebarMinimized", "true");
      } else {
        localStorage.setItem("sidebarMinimized", "false");
      }
    }
  
    // Attach event listener to minimize button
    if (minimizeBtn) {
      minimizeBtn.addEventListener("click", toggleSidebar);
    }
  
    // Restore sidebar state from localStorage on load
    if (localStorage.getItem("sidebarMinimized") === "true") {
      sidebar.classList.add("minimized");
      mainContent.classList.add("expanded");
      const icon = minimizeBtn.querySelector("i");
      icon.classList.remove("fa-chevron-left");
      icon.classList.add("fa-chevron-right");
    }
  
    /**
     * Handles chat heading clicks to switch between chat panels.
     */
    chatHeadings.forEach(function(heading) {
      heading.addEventListener("click", function() {
        // Remove active class from all headings
        chatHeadings.forEach(h => h.classList.remove("active"));
        // Add active class to the clicked heading
        this.classList.add("active");
  
        const chatId = this.getAttribute("data-chat-id");
  
        // Hide all chat panels
        chatPanels.forEach(panel => panel.style.display = "none");
        // Show the selected chat panel
        const selectedPanel = document.querySelector('.chat-panel[data-chat-id="' + chatId + '"]');
        if (selectedPanel) {
          selectedPanel.style.display = "block";
        }
      });
    });
  });