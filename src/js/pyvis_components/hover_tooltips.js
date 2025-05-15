// src/js/pyvis_components/hover_tooltips.js

(function(window) {
    function initHoverTooltips(network) {
        // Vis.js hover should be enabled by default from Python's initial_options.
        // Ensure hoverConnectedEdges is false if that's the desired behavior for Tippy.
        if (network.options.interaction) {
            network.setOptions({ interaction: { hoverConnectedEdges: false } });
        } else {
            // Fallback if interaction options are not set, though unlikely with pyvis_mod.py
            network.setOptions({ interaction: { hover: true, hoverConnectedEdges: false } });
        }

        const tip = tippy(document.body, {
            getReferenceClientRect: () => ({ width:0, height:0, top:0, bottom:0, left:0, right:0 }),
            content: '',
            allowHTML: true,
            theme: 'pyvis-hover', // Custom theme name, style in pyvis_styles.css
            animation: 'fade', 
            delay: [200, 50], // show (200ms), hide (50ms)
            trigger: 'manual', // We control show/hide manually
            placement: 'top-start', 
            arrow: true,
            inertia: false, 
            maxWidth: 350, // Max width for the hover tooltip
            appendTo: () => document.body,
            interactive: false, // Hover tooltips are typically not interactive
        })[0];
        
        network._hoverTip = tip;
        // console.log('Tippy instance for hover stored on network._hoverTip:', tip);

        const container = network.body.container;
        let mouseX = 0, mouseY = 0;
        container.addEventListener('mousemove', e => {
            mouseX = e.clientX;
            mouseY = e.clientY;
        });

        const onTooltipMutated = (mutationsList) => {
            const t = network._hoverTip;
            if (!t) return;

            for (const m of mutationsList) {
                const visTooltipEl = m.target.classList && m.target.classList.contains('vis-tooltip') 
                               ? m.target 
                               : (m.target.parentElement && m.target.parentElement.classList.contains('vis-tooltip') 
                                  ? m.target.parentElement 
                                  : null);

                if (!visTooltipEl) continue;
                
                const hasContent = visTooltipEl.innerHTML.trim() !== '';
                const isPositionedOnScreen = parseFloat(visTooltipEl.style.left) > -5000 && visTooltipEl.style.display === 'block';

                if (isPositionedOnScreen && hasContent) {
                    let fullHtmlContent = visTooltipEl.innerHTML;
                    let briefHoverContent = fullHtmlContent; // Default to full if separator not found

                    const separator = "<div class='pyvis-hover-separator' style='display:none !important;'>---HOVER_END---</div>";
                    const separatorIndex = fullHtmlContent.indexOf(separator);

                    if (separatorIndex !== -1) {
                        briefHoverContent = fullHtmlContent.substring(0, separatorIndex).trim();
                    } else {
                        // console.warn("Pyvis hover separator not found in node title. Full title used for hover.");
                    }
                    
                    if (briefHoverContent.trim() === "") {
                        if (t.state.isShown) t.hide();
                        continue;
                    }

                    t.setProps({
                        content: briefHoverContent,
                        getReferenceClientRect: () => ({
                            width: 0, height: 0,
                            top: mouseY, bottom: mouseY,
                            left: mouseX, right: mouseX,
                        }),
                    });
                    if (!t.state.isShown) { 
                        t.show(); 
                    }
                } else {
                    if (t.state.isShown) { 
                        t.hide(); 
                    }
                }
            }
        };

        const observeVisTooltip = (visEl) => {
            // console.log("Observing .vis-tooltip element for hover tooltips:", visEl);
            const obs = new MutationObserver(onTooltipMutated);
            obs.observe(visEl, { attributes: true, attributeFilter: ['style'], childList: true, subtree: true, characterData: true });
            network._hoverTooltipObserver = obs; 
        };
        
        const initialVisTooltip = container.querySelector('.vis-tooltip');
        if (initialVisTooltip) {
            observeVisTooltip(initialVisTooltip);
        } else {
            // console.log(".vis-tooltip not found initially for hover, observing container for its addition.");
            const tooltipAddObserver = new MutationObserver((mutations, observer) => {
                for (const mutation of mutations) {
                    for (const addedNode of mutation.addedNodes) {
                        if (addedNode.nodeType === 1 && addedNode.classList && addedNode.classList.contains('vis-tooltip')) {
                            // console.log(".vis-tooltip detected and added to DOM (for hover):", addedNode);
                            observeVisTooltip(addedNode);
                            // Do NOT disconnect this observer, Vis.js might remove and re-add its tooltip element
                            // if options change or if it internally recycles the element.
                            // observer.disconnect(); 
                            return; // Found and attached, exit for this specific added node.
                        }
                    }
                }
            });
            tooltipAddObserver.observe(container, { childList: true, subtree: true });
        }
    }
    window.initHoverTooltips = initHoverTooltips;
})(window);