// src/js/pyvis_components/hover_tooltips.js

(function(window) {
    function initHoverTooltips(network) {
        // Disable Vis.js default hover
        network.setOptions({ interaction: { hover: false } });

        network.on('hoverNode', function(params) {
            const id = params.node;
            const domNode = network.body.nodes[id].shape.node;
            const title = network.body.data.nodes.get(id).title || '';
            const tip = tippy(domNode, {
                content: title,
                allowHTML: true,
                theme: 'light-border',
                animation: 'shift-away',
                delay: [100, null],
                trigger: 'manual',
                placement: 'top',
            });
            tip.show();
            network.body.nodes[id]._hoverTip = tip;
        });

        network.on('blurNode', function(params) {
            const id = params.node;
            const nodeObj = network.body.nodes[id];
            if (nodeObj && nodeObj._hoverTip) {
                nodeObj._hoverTip.destroy();
                delete nodeObj._hoverTip;
            }
        });
    }

    window.initHoverTooltips = initHoverTooltips;
})(window);
