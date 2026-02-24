import { ReactElement, useEffect, useId, useRef, useState, useCallback } from 'react';
import mermaid from 'mermaid';

const MermaidChart = ({ chart }: { chart: string }): ReactElement => {

    const id = useId();
    const [svg, setSvg] = useState('');
    const containerRef = useRef(null);

    const renderChart = useCallback(async () => {
        const mermaidConfig = {
            startOnLoad: false,
            securityLevel: 'loose',
            fontFamily: 'inherit',
            themeCSS: 'margin: 1.5rem auto 0;',
            theme: 'default',
        };

        try {
            mermaid.initialize(mermaidConfig);
            const {svg} = await mermaid.render(
                // strip invalid characters for `id` attribute
                id.replaceAll(':', ''),
                chart,
                containerRef.current || undefined,
            );
            setSvg(svg);
        } catch (error) {
            setSvg("<font color='red'>Error while rendering Chart</font>");
            console.error('Error while rendering mermaid', error, chart);
        }


    }, []);

    useEffect(() => {
        renderChart();
    }, [chart]);

    return <div ref={containerRef} dangerouslySetInnerHTML={{ __html: svg }} />;

}

export default MermaidChart;