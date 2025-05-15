// src/js/pyvis_components/hover_tooltips.js

(function(window) {
    function initHoverTooltips(network) {
        // Vis.js hover should be enabled by default from Python's initial_options.
        // We just ensure hoverConnectedEdges is false if that's the desired behavior for Tippy.
        network.setOptions({ interaction: { hoverConnectedEdges: false } });

        const tip = tippy(document.body, {
            getReferenceClientRect: () => ({ width:0, height:0, top:0, bottom:0, left:0, right:0 }),
            content: '',
            allowHTML: true,
            theme: 'light-border', 
            animation: 'shift-away', 
            delay: [150, 50], // Adjusted delay for a slightly quicker appearance
            trigger: 'manual',
            placement: 'top',
            arrow: true,
            inertia: true,
            maxWidth: 350, // Set a max width for hover tooltips
        })[0];
        
        network._hoverTip = tip;
        // console.log('Tippy instance stored on network._hoverTip:', tip);

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
                // Ensure we are targeting the .vis-tooltip element itself or its direct child that changed
                const el = m.target.classList && m.target.classList.contains('vis-tooltip') 
                           ? m.target 
                           : (m.target.parentElement && m.target.parentElement.classList.contains('vis-tooltip') 
                              ? m.target.parentElement 
                              : null);

                if (!el) continue;

                // console.log('Hover observer fired for .vis-tooltip mutation:', el, 'visibility:', el.style.visibility, 'display:', el.style.display, 'opacity:', el.style.opacity, 'innerHTML:', el.innerHTML.substring(0,100));
                
                // Vis.js often uses 'display: block/none' or modifies 'left'/'top' from off-screen.
                // It also might be briefly visible then hidden if content is empty.
                const hasContent = el.innerHTML.trim() !== '';
                const isStyledVisible = el.style.visibility === 'visible' || (el.style.display !== 'none' && el.style.display !== '');
                // Check if it's positioned on screen (Vis.js moves it from -9999px)
                const isPositioned = parseFloat(el.style.left) > -5000 && parseFloat(el.style.top) > -5000;


                if (isStyledVisible && hasContent && isPositioned) {
                    // console.log("Native tooltip is visible with content, showing Tippy.");
                    // For hover tooltips, we usually want something brief.
                    // The full `el.innerHTML` comes from `node.title`.
                    // If `node.title` includes the lengthy definition, we might want to strip it here for the hover.
                    // For now, let's use it as is, but this is a point of refinement.
                    let tippyContent = el.innerHTML;
                    
                    // Optional: Simple way to get only the first part (e.g., before "Definition:")
                    const defMarker = "<b>Definition:</b>";
                    const defIndex = tippyContent.indexOf(defMarker);
                    if (defIndex > 0) { // Check >0 to ensure some base content exists before definition
                        // Take content before the definition, removing potential trailing <br> or divs.
                        let briefContent = tippyContent.substring(0, defIndex);
                        // Remove trailing container div of definition if it was included.
                        const divEndMarker = "<div style='margin-top:10px;"; 
                        const divEndIndex = briefContent.lastIndexOf(divEndMarker);
                        if (divEndIndex > 0 && divEndIndex > briefContent.length - 50) { // Heuristic
                            briefContent = briefContent.substring(0, divEndIndex);
                        }
                        briefContent = briefContent.replace(/<br\s*\/?>\s*$/, ""); // Remove trailing <br>
                        tippyContent = briefContent.trim();
                    }


                    t.setProps({
                        content: tippyContent,
                        getReferenceClientRect: () => ({
                            width: 0, height: 0,
                            top: mouseY, bottom: mouseY,
                            left: mouseX, right: mouseX,
                        }),
                    });
                    if (!t.state.isShown) { t.show(); }
                } else {
                    if (t.state.isShown) { t.hide(); }
                }
            }
        };

        const observeTooltipElement = (visEl) => {
            // console.log("Observing .vis-tooltip element for hover:", visEl);
            const obs = new MutationObserver(onTooltipMutated);
            obs.observe(visEl, { attributes: true, attributeFilter: ['style'], childList: true, subtree: true, characterData: true });
        };

        let visTooltip = container.querySelector('.vis-tooltip');
        if (visTooltip) {
            observeTooltipElement(visTooltip);
        } else {
            // console.log(".vis-tooltip not found initially for hover, observing container for additions.");
            const addObserver = new MutationObserver((mutations, observerInstance) => {
                for (const m of mutations) {
                    m.addedNodes.forEach(node => {
                        if (node.nodeType === 1 && node.classList && node.classList.contains('vis-tooltip')) {
                            // console.log(".vis-tooltip added to DOM (for hover):", node);
                            observeTooltipElement(node);
                            // Do not disconnect this one, Vis.js might remove and re-add its tooltip element
                            // observerInstance.disconnect(); 
                        }
                    });
                }
            });
            addObserver.observe(container, { subtree: true, childList: true });
        }
    }
    window.initHoverTooltips = initHoverTooltips;
})(window);