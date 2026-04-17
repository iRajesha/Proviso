-- =============================================================
-- Proviso APEX AJAX Callbacks (PL/SQL)
-- Add each as an "AJAX Callback" process on the respective page
-- =============================================================

-- ---------------------------------------------------------------
-- Process: GENERATE_INFRA (Page 1)
-- ---------------------------------------------------------------
DECLARE
    l_requirements VARCHAR2(32767) := apex_application.g_x01;
    l_services     VARCHAR2(4000)  := apex_application.g_x02;
    l_body         CLOB;
    l_response     CLOB;
    l_http_status  NUMBER;
BEGIN
    -- Build JSON payload
    l_body := '{"requirements":' || apex_json.stringify(l_requirements) ||
              ',"services":[' ||
              REPLACE(
                  '"' || REPLACE(l_services, ',', '","') || '"',
                  '""', ''
              ) || ']}';

    apex_web_service.g_request_headers(1).name  := 'Content-Type';
    apex_web_service.g_request_headers(1).value := 'application/json';

    l_response := apex_web_service.make_rest_request(
        p_url         => 'http://localhost:8000/api/v1/generate',
        p_http_method => 'POST',
        p_body        => l_body
    );

    htp.prn(l_response);
END;

-- ---------------------------------------------------------------
-- Process: SAVE_SCRIPT (Page 1)
-- ---------------------------------------------------------------
DECLARE
    l_payload  VARCHAR2(32767) := apex_application.g_x01;
    l_response CLOB;
BEGIN
    apex_web_service.g_request_headers(1).name  := 'Content-Type';
    apex_web_service.g_request_headers(1).value := 'application/json';

    l_response := apex_web_service.make_rest_request(
        p_url         => 'http://localhost:8000/api/v1/scripts/save',
        p_http_method => 'POST',
        p_body        => l_payload
    );

    htp.prn(l_response);
END;

-- ---------------------------------------------------------------
-- Process: SEARCH_SCRIPTS (Page 2)
-- ---------------------------------------------------------------
DECLARE
    l_query    VARCHAR2(4000) := apex_application.g_x01;
    l_response CLOB;
BEGIN
    apex_web_service.g_request_headers(1).name  := 'Content-Type';
    apex_web_service.g_request_headers(1).value := 'application/json';

    l_response := apex_web_service.make_rest_request(
        p_url         => 'http://localhost:8000/api/v1/scripts/search',
        p_http_method => 'POST',
        p_body        => '{"query":' || apex_json.stringify(l_query) || ',"limit":20}'
    );

    htp.prn(l_response);
END;

-- ---------------------------------------------------------------
-- Process: GET_SCRIPT (Page 2)
-- ---------------------------------------------------------------
DECLARE
    l_id       NUMBER         := TO_NUMBER(apex_application.g_x01);
    l_response CLOB;
BEGIN
    l_response := apex_web_service.make_rest_request(
        p_url         => 'http://localhost:8000/api/v1/scripts/' || l_id,
        p_http_method => 'GET'
    );

    htp.prn(l_response);
END;
