#include <windows.h>
#include <dshow.h>
#include <stdio.h>

// Define CLSID_NullRenderer and CLSID_SampleGrabber
static const CLSID CLSID_NullRenderer = {0xC1F400A4, 0x3F08, 0x11D3, {0x9F, 0x0B, 0x00, 0x60, 0x08, 0x03, 0x9E, 0x37}};
static const CLSID CLSID_SampleGrabber = {0xC1F400A0, 0x3F08, 0x11D3, {0x9F, 0x0B, 0x00, 0x60, 0x08, 0x03, 0x9E, 0x37}};
static const IID IID_ISampleGrabber = {0x6B652FFF, 0x11FE, 0x4FCE, {0x92, 0xAD, 0x02, 0x66, 0xB5, 0xD7, 0xC7, 0x8F}};

// Manually define ISampleGrabber interface
typedef struct ISampleGrabber ISampleGrabber;
typedef struct ISampleGrabberVtbl {
    HRESULT (STDMETHODCALLTYPE *QueryInterface)(ISampleGrabber*, REFIID, void**);
    ULONG (STDMETHODCALLTYPE *AddRef)(ISampleGrabber*);
    ULONG (STDMETHODCALLTYPE *Release)(ISampleGrabber*);
    HRESULT (STDMETHODCALLTYPE *SetOneShot)(ISampleGrabber*, BOOL);
    HRESULT (STDMETHODCALLTYPE *SetMediaType)(ISampleGrabber*, const AM_MEDIA_TYPE*);
    HRESULT (STDMETHODCALLTYPE *GetConnectedMediaType)(ISampleGrabber*, AM_MEDIA_TYPE*);
    HRESULT (STDMETHODCALLTYPE *SetBufferSamples)(ISampleGrabber*, BOOL);
    HRESULT (STDMETHODCALLTYPE *GetCurrentBuffer)(ISampleGrabber*, long*, long*);
    HRESULT (STDMETHODCALLTYPE *GetCurrentSample)(ISampleGrabber*, IMediaSample**);
    HRESULT (STDMETHODCALLTYPE *SetCallback)(ISampleGrabber*, void*, long);
} ISampleGrabberVtbl;

struct ISampleGrabber {
    const ISampleGrabberVtbl* lpVtbl;
};

__declspec(dllexport) int capturePhoto(const char* outputFile) {
    HRESULT hr;
    IGraphBuilder* pGraph = NULL;
    ICaptureGraphBuilder2* pBuilder = NULL;
    IBaseFilter* pCap = NULL;
    IBaseFilter* pSampleGrabberFilter = NULL;
    ISampleGrabber* pSampleGrabber = NULL;
    IBaseFilter* pNullRenderer = NULL;
    IMoniker* pMoniker = NULL;
    IEnumMoniker* pEnum = NULL;
    IMediaControl* pControl = NULL;

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

    // Create the SampleGrabber filter
    hr = CoCreateInstance(&CLSID_SampleGrabber, NULL, CLSCTX_INPROC_SERVER, 
                          &IID_IBaseFilter, (void**)&pSampleGrabberFilter);
    if (FAILED(hr)) goto cleanup;

    hr = pSampleGrabberFilter->lpVtbl->QueryInterface(pSampleGrabberFilter, &IID_ISampleGrabber, (void**)&pSampleGrabber);
    if (FAILED(hr)) goto cleanup;

    // Configure SampleGrabber
    AM_MEDIA_TYPE mt;
    ZeroMemory(&mt, sizeof(AM_MEDIA_TYPE));
    mt.majortype = MEDIATYPE_Video;
    mt.subtype = MEDIASUBTYPE_RGB24; // Raw RGB24 data
    hr = pSampleGrabber->lpVtbl->SetMediaType(pSampleGrabber, &mt);
    if (FAILED(hr)) goto cleanup;

    hr = pSampleGrabber->lpVtbl->SetOneShot(pSampleGrabber, TRUE); // Capture one frame
    if (FAILED(hr)) goto cleanup;

    hr = pSampleGrabber->lpVtbl->SetBufferSamples(pSampleGrabber, TRUE); // Buffer the sample
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

    // Add filters to graph
    hr = pGraph->lpVtbl->AddFilter(pGraph, pCap, L"Capture Filter");
    if (FAILED(hr)) goto cleanup;

    hr = pGraph->lpVtbl->AddFilter(pGraph, pSampleGrabberFilter, L"Sample Grabber");
    if (FAILED(hr)) goto cleanup;

    hr = CoCreateInstance(&CLSID_NullRenderer, NULL, CLSCTX_INPROC_SERVER, 
                          &IID_IBaseFilter, (void**)&pNullRenderer);
    if (FAILED(hr)) goto cleanup;

    hr = pGraph->lpVtbl->AddFilter(pGraph, pNullRenderer, L"Null Renderer");
    if (FAILED(hr)) goto cleanup;

    // Set up the graph
    hr = pBuilder->lpVtbl->SetFiltergraph(pBuilder, pGraph);
    if (FAILED(hr)) goto cleanup;

    // Connect capture -> SampleGrabber -> null renderer
    hr = pBuilder->lpVtbl->RenderStream(pBuilder, &PIN_CATEGORY_CAPTURE, &MEDIATYPE_Video, 
                                        pCap, pSampleGrabberFilter, pNullRenderer);
    if (FAILED(hr)) goto cleanup;

    // Get media control
    hr = pGraph->lpVtbl->QueryInterface(pGraph, &IID_IMediaControl, (void**)&pControl);
    if (FAILED(hr)) goto cleanup;

    // Run the graph
    hr = pControl->lpVtbl->Run(pControl);
    if (FAILED(hr)) goto cleanup;

    // Wait briefly
    Sleep(1000); // Increased to ensure frame capture

    // Stop the graph
    pControl->lpVtbl->Stop(pControl);

    // Get the captured buffer
    long bufferSize = 0;
    hr = pSampleGrabber->lpVtbl->GetCurrentBuffer(pSampleGrabber, &bufferSize, NULL);
    if (FAILED(hr) || bufferSize <= 0) goto cleanup;

    BYTE* buffer = (BYTE*)malloc(bufferSize);
    if (!buffer) goto cleanup;

    hr = pSampleGrabber->lpVtbl->GetCurrentBuffer(pSampleGrabber, &bufferSize, (long*)buffer);
    if (FAILED(hr)) {
        free(buffer);
        goto cleanup;
    }

    // Get the connected media type to determine width and height
    AM_MEDIA_TYPE connectedMt;
    ZeroMemory(&connectedMt, sizeof(AM_MEDIA_TYPE));
    hr = pSampleGrabber->lpVtbl->GetConnectedMediaType(pSampleGrabber, &connectedMt);
    if (FAILED(hr)) {
        free(buffer);
        goto cleanup;
    }

    VIDEOINFOHEADER* vih = (VIDEOINFOHEADER*)connectedMt.pbFormat;
    int width = vih->bmiHeader.biWidth;
    int height = vih->bmiHeader.biHeight; // Might be negative (top-down BMP)

    // Write BMP file
    FILE* fp = fopen(outputFile, "wb");
    if (fp) {
        BITMAPFILEHEADER bfh = {0};
        BITMAPINFOHEADER bih = {0};

        // BITMAPFILEHEADER
        bfh.bfType = 0x4D42; // "BM"
        bfh.bfOffBits = sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER);
        bfh.bfSize = bfh.bfOffBits + bufferSize;

        // BITMAPINFOHEADER
        bih.biSize = sizeof(BITMAPINFOHEADER);
        bih.biWidth = width;
        bih.biHeight = height; // Use as-is (negative for top-down)
        bih.biPlanes = 1;
        bih.biBitCount = 24;
        bih.biCompression = BI_RGB;
        bih.biSizeImage = bufferSize;

        fwrite(&bfh, sizeof(BITMAPFILEHEADER), 1, fp);
        fwrite(&bih, sizeof(BITMAPINFOHEADER), 1, fp);
        fwrite(buffer, bufferSize, 1, fp);
        fclose(fp);
    }

    free(buffer);
    if (connectedMt.pbFormat) CoTaskMemFree(connectedMt.pbFormat);

cleanup:
    if (pControl) pControl->lpVtbl->Release(pControl);
    if (pSampleGrabber) pSampleGrabber->lpVtbl->Release(pSampleGrabber);
    if (pSampleGrabberFilter) pSampleGrabberFilter->lpVtbl->Release(pSampleGrabberFilter);
    if (pNullRenderer) pNullRenderer->lpVtbl->Release(pNullRenderer);
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