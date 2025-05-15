// src/js/pyvis_components/hover_tooltips.js

(function(window) {
    function initHoverTooltips(network) {
        // Re-enable Vis.js hover (we'll hijack the native tooltip)
        network.setOptions({ interaction: { hover: true, hoverConnectedEdges: false } });

        // Create a single Tippy instance bound to document.body
        const tip = tippy(document.body, {
            getReferenceClientRect: () => ({ width: 0, height: 0, top: 0, bottom: 0, left: 0, right: 0 }),
            content: '',
            allowHTML: true,
            theme: 'light-border',
            animation: 'shift-away',
            delay: [100, null],
            trigger: 'manual',
            placement: 'top',
        })[0];
        // Store for observer callback
        network._hoverTip = tip;

        // Track mouse position for positioning the Tippy
        const container = network.body.container;
        let mouseX = 0, mouseY = 0;
        container.addEventListener('mousemove', e => {
            mouseX = e.clientX;
            mouseY = e.clientY;
        });

        // MutationObserver callback: watch .vis-tooltip style changes
        const onTooltipMutated = (mutationsList) => {
            const t = network._hoverTip;
            if (!t) return;
            for (const m of mutationsList) {
                const el = m.target;
                if (el.style.visibility === 'visible') {
                    // Show our Tippy at the last mouse pos with the same content
                    t.setProps({
                        content: el.innerHTML,
                        getReferenceClientRect: () => ({
                            width: 0, height: 0,
                            top: mouseY, bottom: mouseY,
                            left: mouseX, right: mouseX,
                        }),
                    });
                    t.show();
                } else {
                    t.hide();
                }
            }
        };

        // Attach observer to existing or future .vis-tooltip elements
        const observeTooltipElement = (visEl) => {
            const obs = new MutationObserver(onTooltipMutated);
            obs.observe(visEl, { attributes: true, attributeFilter: ['style'] });
        };

        // Try existing element anywhere in the document
        let visTooltip = document.querySelector('.vis-tooltip');
        if (visTooltip) {
            observeTooltipElement(visTooltip);
        } else {
            // Watch for additions of .vis-tooltip under document.body
            const addObserver = new MutationObserver(mutations => {
                for (const m of mutations) {
                    for (const node of m.addedNodes) {
                        if (node.classList && node.classList.contains('vis-tooltip')) {
                            observeTooltipElement(node);
                        }
                    }
                }
            });
            addObserver.observe(document.body, { subtree: true, childList: true });
        }
    }

    // Expose init function
    window.initHoverTooltips = initHoverTooltips;
})(window);
