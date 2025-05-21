// src/js/pyvis_components/core.js

// Pyvis custom JavaScript - Core
// Placeholders: %%INITIAL_NETWORK_OPTIONS%%, %%BASE_FILE_NAME%%

const initialNetworkOptions = "%%INITIAL_NETWORK_OPTIONS%%";
const baseFileName = "%%BASE_FILE_NAME%%";

// --- Global State Variables ---
let isPanelExpanded = false;
const panelWidth = 300; // Match CSS for controlPanel
let loadingTimeout = null; // For fallback hide timer for loading overlay

// --- Selection State Variables ---
let isSelecting = false;
let selectionStartX = 0;
let selectionStartY = 0;
let selectionRect = { x: 0, y: 0, width: 0, height: 0 }; // Store selection rect relative to overlay
let selectionCanvasCoords = null; // To store converted canvas coordinates

// --- DOM Element Placeholders (to be assigned in init.js or respective modules) ---
let selectionOverlay = null;
let selectionRectangle = null;
let exportChoiceModal = null;

// --- Search Variables ---
let searchPanel = null;
let searchInput = null;
let searchResultCount = null;
let searchStatus = null;
let prevSearchResultBtn = null;
let nextSearchResultBtn = null;
let currentSearchQuery = "";
let currentSearchResults = [];
let currentSearchResultIndex = -1;
let searchFuseInstance = null;
let isSearchPanelOpen = false;

// --- Network Ready State ---
let networkReady = false;
let listenersAttached = false;

// --- Persistent Tooltip State ---
let persistentTooltip = null;
let persistentTooltipNodeId = null;
let nodeEditState = {
    nodeId: null,
    addParents: [],
    addChildren: [],
    removeParents: [],
    removeChildren: [],
    deleted: false,
};

// Note: The `network` variable is globally provided by vis.js and will be checked for existence.
// Global `window.network` is assumed.