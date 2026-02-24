import React, {useEffect, useRef, useState, useCallback, memo } from 'react';
import axios from "axios";
import { apiUrl } from "../../libs/api-base";

function TikzPicture ({code}: any) {
    const [svg, setSvg] = useState('');
    const containerRef = useRef(null);

    const renderImage = useCallback(async () => {

        try {
            const response = await axios({
                method: 'post',
                url: apiUrl('/rest/tikzjax'),
                headers: { 'Content-Type': 'application/json' },
                data: { source: code }
            });

            if (response.data.error) {
                throw response.data.error;
            } else {
                setSvg(response.data.payload);
            }
            
        } catch (error) {
            setSvg("<font color='red'>Error while rendering image</font>");
            console.error('Error while rendering mermaid', error, code);
        }


    }, []);

    useEffect(() => {
        renderImage();
    }, [code]);

    return <div ref={containerRef} dangerouslySetInnerHTML={{ __html: svg }} />;
}

export default memo(TikzPicture)
