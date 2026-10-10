import pytest
from fastapi.testclient import TestClient
from backend.app.main import Base, app, engine, init_db

@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    init_db()
    with TestClient(app) as client:
        yield client
    Base.metadata.drop_all(bind=engine)

def login(client, email="owner@aramesh.local", password="Owner@12345"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]

def auth(token):
    return {"Authorization": "Bearer " + token}

def order_for(client, product, token=None, key=None):
    return client.post("/api/orders", headers=auth(token) if token else {}, json={
        "table_token":"T01", "items":[{"kind":"product","id":product["id"],"quantity":1}],
        "idempotency_key":key
    })

def confirm_and_serve(client, order, waiter):
    result=client.post(f"/api/staff/orders/{order['id']}/verify",headers=auth(waiter),json={"code":order["confirmation_code"]})
    assert result.status_code==200,result.text
    for state in ("preparing","ready","served"):
        result=client.patch(f"/api/staff/orders/{order['id']}/status",headers=auth(waiter),json={"status":state})
        assert result.status_code==200,result.text

def test_health_and_seeded_menu(client):
    assert client.get("/api/health").json()["status"]=="ok"
    menu=client.get("/api/menu").json()
    assert len(menu["products"])>=10
    assert len(menu["categories"])==4

def test_role_permissions(client):
    owner=login(client)
    waiter=login(client,"waiter@aramesh.local","Waiter@12345")
    member=login(client,"member@aramesh.local","Member@12345")
    assert client.get("/api/merchant/analytics",headers=auth(owner)).status_code==200
    assert client.get("/api/merchant/analytics",headers=auth(waiter)).status_code==403
    assert client.get("/api/merchant/products",headers=auth(member)).status_code==403
    assert client.get("/api/staff/orders",headers=auth(owner)).status_code==403

def test_persian_search(client):
    result=client.get("/api/search/natural",params={"query":"یه چیز سرد و ترش می‌خوام"}).json()
    assert result["provider"]=="rule-based"
    assert result["matches"][0]["name"]=="لیموناد خانگی"
    result=client.get("/api/search/natural",params={"query":"قهوه قوی برای درس خوندن"}).json()
    assert "اسپرسو دوبل" in {p["name"] for p in result["matches"]}

def test_order_server_price_idempotency_and_code_privacy(client):
    waiter=login(client,"waiter@aramesh.local","Waiter@12345")
    product=next(p for p in client.get("/api/menu").json()["products"] if p["name"]=="اسپرسو دوبل")
    response=order_for(client,product,key="idempotent-test")
    assert response.status_code==200,response.text
    order=response.json()
    assert order["total_toman"]==product["price_toman"]
    assert order["status"]=="pending_verification"
    assert len(order["confirmation_code"])==4
    assert order_for(client,product,key="idempotent-test").status_code==409
    queue=client.get("/api/staff/orders",headers=auth(waiter)).json()
    visible=next(x for x in queue if x["id"]==order["id"])
    assert "confirmation_code" not in visible
    assert client.post(f"/api/staff/orders/{order['id']}/verify",headers=auth(waiter),json={"code":"۰۰۰۰"}).status_code==400
    assert client.post(f"/api/staff/orders/{order['id']}/verify",headers=auth(waiter),json={"code":order["confirmation_code"]}).status_code==200

def test_loyalty_awards_only_after_serving(client):
    member=login(client,"member@aramesh.local","Member@12345")
    waiter=login(client,"waiter@aramesh.local","Waiter@12345")
    product=next(p for p in client.get("/api/menu").json()["products"] if p["name"]=="اسپرسو دوبل")
    order=order_for(client,product,token=member).json()
    assert client.get("/api/loyalty/me",headers=auth(member)).json()["points"]==0
    confirm_and_serve(client,order,waiter)
    loyalty=client.get("/api/loyalty/me",headers=auth(member)).json()
    assert loyalty["points"]>=1
    assert len(loyalty["history"])==1

def test_work_mode_requires_confirmed_eligible_order(client):
    member=login(client,"member@aramesh.local","Member@12345")
    waiter=login(client,"waiter@aramesh.local","Waiter@12345")
    product=next(p for p in client.get("/api/menu").json()["products"] if p["name"]=="اسپرسو دوبل")
    order=order_for(client,product,token=member).json()
    body={"order_id":order["id"],"duration_minutes":120}
    assert client.post("/api/work-mode/sessions",headers=auth(member),json=body).status_code==403
    assert client.post(f"/api/staff/orders/{order['id']}/verify",headers=auth(waiter),json={"code":order["confirmation_code"]}).status_code==200
    session=client.post("/api/work-mode/sessions",headers=auth(member),json=body)
    assert session.status_code==200,session.text
    assert session.json()["status"]=="active"

def test_analytics_excludes_pending_requests(client):
    owner=login(client)
    product=client.get("/api/menu").json()["products"][0]
    order_for(client,product)
    result=client.get("/api/merchant/analytics?period=month",headers=auth(owner)).json()
    assert result["current_period"]["completed_orders"]==0
    assert result["changes"]["completed_orders_percent"] is None
