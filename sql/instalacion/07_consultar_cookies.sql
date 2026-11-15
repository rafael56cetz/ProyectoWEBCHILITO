-- Solo lectura. Muestra las decisiones de cookies guardadas. Query Tool, como chilito_pkg_owner.
-- Sin nombres ni correos: el sujeto es un identificador seudónimo del navegador.
SELECT d.registrada_en AS fecha,
       CASE WHEN d.decision THEN 'Aceptó estadísticas' ELSE 'Rechazó estadísticas' END AS decision,
       s.id AS sujeto_navegador,
       s.usuario_id IS NOT NULL AS vinculada_a_cuenta,
       aviso.version AS version_aviso,
       politica.version AS version_politica,
       p.decision_id IS NOT NULL AS es_la_vigente
FROM public.privacidad_decisionprivacidad d
JOIN public.privacidad_sujetoprivacidad s ON s.id = d.sujeto_id
JOIN public.privacidad_documentoversion aviso ON aviso.id = d.documento_id
JOIN public.privacidad_documentoversion politica ON politica.id = d.politica_cookies_id
LEFT JOIN public.privacidad_preferenciafinalidad p ON p.decision_id = d.id
WHERE d.acto = 'cookies'
ORDER BY d.registrada_en DESC;
