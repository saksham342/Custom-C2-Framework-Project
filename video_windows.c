#include <windows.h>
#include <dshow.h>
#include <stdio.h>

// Define necessary CLSIDs
static const CLSID CLSID_AviDest = {0xE2510970, 0xF137, 0x11CE, {0x8B, 0x67, 0x00, 0xAA, 0x00, 0xA3, 0xF1, 0xA6}}; // AVI Mux
static const CLSID CLSID_FileWriter = {0x8596E5F0, 0x0DA5, 0x11D0, {0xBD, 0x21, 0x00, 0xA0, 0xC9, 0x11, 0xCE, 0x86}}; // File Writer

// Custom DeleteMediaType to free AM_MEDIA_TYPE
static void DeleteMediaType(AM_MEDIA_TYPE* pmt) {
    if (pmt) {
        if (pmt->pbFormat) {
            CoTaskMemFree(pmt->pbFormat);
            pmt->pbFormat = NULL;
        }
        CoTaskMemFree(pmt);
    }
}

__declspec(dllexport) int captureVideo(const char* outputFile, int durationSeconds, int fps) {
    HRESULT hr;
    IGraphBuilder* pGraph = NULL;
    ICaptureGraphBuilder2* pBuilder = NULL;
    IBaseFilter* pCap = NULL;
    IBaseFilter* pAviMux = NULL;
    IBaseFilter* pFileWriter = NULL;
    IFileSinkFilter* pSink = NULL;
    IMoniker* pMoniker = NULL;
    IEnumMoniker* pEnum = NULL;
    IMediaControl* pControl = NULL;
    IAMStreamConfig* pConfig = NULL;
    IPin* pCapturePin = NULL;

    // Initialize COM
    hr = CoInitialize(NULL);
    if (FAILED(hr)) return -1;

    // Create the filter graph
    hr = CoCreateInstance(&CLSID_FilterGraph, NULL, CLSCTX_INPROC_SERVER, 
                          &IID_IGraphBuilder, (void**)&pGraph);
    if (FAILED(hr)) goto cleanup;

    // Create the capture graph builder
    hr = CoCreateInstance(&CLSID_CaptureGraphBuilder2, NULL, CLSCTX_INPROC_SERVER, 
                          &IID_ICaptureGraphBuilder2, (void**)&pBuilder);
    if (FAILED(hr)) goto cleanup;

    // Enumerate video capture devices
    ICreateDevEnum* pDevEnum = NULL;
    hr = CoCreateInstance(&CLSID_SystemDeviceEnum, NULL, CLSCTX_INPROC_SERVER, 
                          &IID_ICreateDevEnum, (void**)&pDevEnum);
    if (FAILED(hr)) goto cleanup;

    hr = pDevEnum->lpVtbl->CreateClassEnumerator(pDevEnum, &CLSID_VideoInputDeviceCategory, &pEnum, 0);
    if (FAILED(hr) || pEnum == NULL) goto cleanup;

    hr = pEnum->lpVtbl->Next(pEnum, 1, &pMoniker, NULL);
    if (hr != S_OK) goto cleanup;

    hr = pMoniker->lpVtbl->BindToObject(pMoniker, NULL, NULL, &IID_IBaseFilter, (void**)&pCap);
    if (FAILED(hr)) goto cleanup;

    // Add capture filter to graph
    hr = pGraph->lpVtbl->AddFilter(pGraph, pCap, L"Capture Filter");
    if (FAILED(hr)) goto cleanup;

    // Get the capture pin and configure FPS
#pragma warning(suppress : 4133) // Suppress type mismatch warning
    hr = pBuilder->lpVtbl->FindPin(pBuilder, (IUnknown*)pCap, PINDIR_OUTPUT, &PIN_CATEGORY_CAPTURE, &MEDIATYPE_Video, FALSE, 0, (void**)&pCapturePin);
    if (FAILED(hr)) goto cleanup;

    hr = pCapturePin->lpVtbl->QueryInterface(pCapturePin, &IID_IAMStreamConfig, (void**)&pConfig);
    if (FAILED(hr)) goto cleanup;

    AM_MEDIA_TYPE* pmt = NULL;
    hr = pConfig->lpVtbl->GetFormat(pConfig, &pmt);
    if (FAILED(hr)) goto cleanup;

    VIDEOINFOHEADER* vih = (VIDEOINFOHEADER*)pmt->pbFormat;
    vih->AvgTimePerFrame = (LONGLONG)(10000000 / fps); // 100ns units (e.g., 30 FPS = 333333)
    hr = pConfig->lpVtbl->SetFormat(pConfig, pmt);
    if (FAILED(hr)) {
        DeleteMediaType(pmt);
        goto cleanup;
    }
    DeleteMediaType(pmt);

    // Create AVI mux filter
    hr = CoCreateInstance(&CLSID_AviDest, NULL, CLSCTX_INPROC_SERVER, 
                          &IID_IBaseFilter, (void**)&pAviMux);
    if (FAILED(hr)) goto cleanup;

    hr = pGraph->lpVtbl->AddFilter(pGraph, pAviMux, L"AVI Mux");
    if (FAILED(hr)) goto cleanup;

    // Create file writer filter
    hr = CoCreateInstance(&CLSID_FileWriter, NULL, CLSCTX_INPROC_SERVER, 
                          &IID_IBaseFilter, (void**)&pFileWriter);
    if (FAILED(hr)) goto cleanup;

    hr = pGraph->lpVtbl->AddFilter(pGraph, pFileWriter, L"File Writer");
    if (FAILED(hr)) goto cleanup;

    // Set output file
    hr = pFileWriter->lpVtbl->QueryInterface(pFileWriter, &IID_IFileSinkFilter, (void**)&pSink);
    if (FAILED(hr)) goto cleanup;

    WCHAR wOutputFile[MAX_PATH];
    MultiByteToWideChar(CP_ACP, 0, outputFile, -1, wOutputFile, MAX_PATH);
    hr = pSink->lpVtbl->SetFileName(pSink, wOutputFile, NULL);
    if (FAILED(hr)) goto cleanup;

    // Set up the graph
    hr = pBuilder->lpVtbl->SetFiltergraph(pBuilder, pGraph);
    if (FAILED(hr)) goto cleanup;

    // Connect capture filter to AVI mux to file writer
#pragma warning(suppress : 4133) // Suppress type mismatch warning
    hr = pBuilder->lpVtbl->RenderStream(pBuilder, &PIN_CATEGORY_CAPTURE, &MEDIATYPE_Video, 
                                        (IUnknown*)pCap, pAviMux, pFileWriter);
    if (FAILED(hr)) goto cleanup;

    // Get media control
    hr = pGraph->lpVtbl->QueryInterface(pGraph, &IID_IMediaControl, (void**)&pControl);
    if (FAILED(hr)) goto cleanup;

    // Run the graph
    hr = pControl->lpVtbl->Run(pControl);
    if (FAILED(hr)) goto cleanup;

    // Record for the specified duration
    Sleep(durationSeconds * 1000);

    // Stop the graph
    hr = pControl->lpVtbl->Stop(pControl);
    if (FAILED(hr)) goto cleanup;

cleanup:
    if (pControl) pControl->lpVtbl->Release(pControl);
    if (pSink) pSink->lpVtbl->Release(pSink);
    if (pFileWriter) pFileWriter->lpVtbl->Release(pFileWriter);
    if (pAviMux) pAviMux->lpVtbl->Release(pAviMux);
    if (pConfig) pConfig->lpVtbl->Release(pConfig);
    if (pCapturePin) pCapturePin->lpVtbl->Release(pCapturePin);
    if (pCap) pCap->lpVtbl->Release(pCap);
    if (pMoniker) pMoniker->lpVtbl->Release(pMoniker);
    if (pEnum) pEnum->lpVtbl->Release(pEnum);
    if (pDevEnum) pDevEnum->lpVtbl->Release(pDevEnum);
    if (pBuilder) pBuilder->lpVtbl->Release(pBuilder);
    if (pGraph) pGraph->lpVtbl->Release(pGraph);
    CoUninitialize();

    return SUCCEEDED(hr) ? 0 : -1;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
    return TRUE;
}