from app import models
import yfinance
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from pydantic import BaseModel
from app.models import Stock

app = FastAPI()
templates = Jinja2Templates(directory="templates")

models.Base.metadata.create_all(bind=engine)


class StockRequest(BaseModel):
    symbol: str


def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


@app.get("/")
def home(request: Request, forward_pe=None, dividend_yield=None, ma50=None, ma200=None, db: Session = Depends(get_db)):
    """
    display te stock screen dashboard / home page
    :return:
    """
    stocks = db.query(Stock)

    if forward_pe:
        stocks = stocks.filter(Stock.forward_pe < forward_pe)

    if dividend_yield:
        stocks = stocks.filter(Stock.dividend_yield > dividend_yield)

    if ma50:
        stocks = stocks.filter(Stock.price > Stock.ma50)

    if ma200:
        stocks = stocks.filter(Stock.price > Stock.ma200)

    return templates.TemplateResponse("home.html", context={
        "request": request,
        "stocks": stocks,
        "dividend_yield": dividend_yield,
        "forward_pe": forward_pe,
        "ma200": ma200,
        "ma50": ma50
    })


def fetch_stock_data(id: int):
    db = SessionLocal()
    stock = db.query(Stock).filter(Stock.id == id).first()

    yahoo_data = yfinance.Ticker(stock.symbol)

    stock.ma200 = yahoo_data.info['twoHundredDayAverage']
    stock.ma50 = yahoo_data.info['fiftyDayAverage']
    stock.price = yahoo_data.info['previousClose']
    stock.forward_pe = yahoo_data.info['forwardPE']
    stock.forward_eps = yahoo_data.info['forwardEps']
    if yahoo_data.info['dividendYield'] is not None:
        stock.dividend_yield = yahoo_data.info['dividendYield'] * 100

    db.add(stock)
    db.commit()


@app.post("/stock")
async def create_stock(stock_request: StockRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):

    stock = Stock()
    stock.symbol = stock_request.symbol
    db.add(stock)
    db.commit()

    background_tasks.add_task(fetch_stock_data, stock.id)

    return {
        "code": "success",
        "message": "stock created"
    }




