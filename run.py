import uvicorn

if __name__ == "__main__":
    print("Iniciando JMB PERFORMANCE na rede em http://0.0.0.0:8080 ...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=False)
