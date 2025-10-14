
from fastapi import APIRouter, Body, Depends, HTTPException, status
from utils.auth_util import  get_current_user
from database.db import admin_db, user_db, user_transaction_db
from bson import ObjectId
from typing import Optional
from datetime import datetime

router = APIRouter(prefix='/api/v1/admin', tags=['Admin'])

from datetime import datetime, timedelta
from fastapi import Query
# Dashboard endpoint for stats
@router.get('/dashboard')
async def get_dashboard_stats(period: str = Query('30d'), current_user: dict = Depends(get_current_user)):
    # Parse period (e.g., '30d', '7d', '1d')
    try:
        days = int(period.replace('d', ''))
    except:
        days = 30
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Total users (excluding admin)
    user_count = await user_db.count_documents({"role": {"$ne": "admin"}})

    # Total revenue (sum of game_fee in user_transactions)
    total_revenue = await user_transaction_db.aggregate([
        {"$match": {"type": "game_fee", "created_at": {"$gte": start_date, "$lte": end_date}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(length=1)
    total_revenue = total_revenue[0]["total"] if total_revenue else 0

    # Revenue by day
    pipeline = [
        {"$match": {"type": "game_fee", "created_at": {"$gte": start_date, "$lte": end_date}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "total": {"$sum": "$amount"}
        }},
        {"$sort": {"_id": 1}}
    ]
    revenue_by_day = await user_transaction_db.aggregate(pipeline).to_list(length=None)
    revenue_by_day = [{"date": r["_id"], "total": r["total"]} for r in revenue_by_day]

    return {
        "totalUsers": user_count,
        "totalRevenue": total_revenue,
        "revenueByDay": revenue_by_day
    }
@router.patch("/update-upi_id")
# async def update_upi_id(new_upi: str = Body(..., embed=True),current_user: dict = Depends(admin_role)):
async def update_upi_id(new_upi: str = Body(..., embed=True),current_user: dict = Depends(get_current_user)):

    try:
        admin_id = current_user["sub"]
          
        result = await admin_db.update_one(
        {"user_id": ObjectId(admin_id)},
        {"$set": {"upi_id": new_upi}},
        upsert=True  # create if not exists
        )
        if result.upserted_id:
            return {"message": "UPI ID created successfully for admin."}
        elif result.modified_count > 0:
            return {"message": "UPI ID updated successfully."}
        else:
            return {"message": "No changes made (UPI already same)."}
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Error updating UPI ID: {str(e)}")   

@router.get('/upi_id')
async def get_upi_id(current_user: dict = Depends(get_current_user)):
    try:
        admin_id = current_user['sub']
        result = await admin_db.find_one({'user_id': ObjectId(admin_id)})
        if not result:
            raise HTTPException(status_code=404, detail="Admin profile not found")
        
        upi_id = result.get('upi_id')
        if not upi_id:
            raise HTTPException(status_code=404, detail="UPI ID not set for this admin")
            
        return {"data": upi_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching UPI ID: {str(e)}"
        )
        
@router.get('/get_all_users')
async def get_all_users(current_user: dict = Depends(get_current_user)):
    try:
        # users_cursor = user_db.find({"role": {"$ne": "admin"}}, {"password": 0})
        users_cursor = user_db.find({}, {"password": 0})
        users = []
        async for user in users_cursor:
            user["_id"] = str(user["_id"])
            users.append(user)
        return {"users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")

@router.get('/all_wallet_data')
async def get_all_wallet_data(current_user: dict = Depends(get_current_user)):
    try:
        pipeline = [
        {
            "$group": {
                "_id": {"$toString": "$type"},
                "total_amount": {"$sum": "$amount"},
                "count": {"$sum": 1}
            }
        }
        ]
        result = await user_transaction_db.aggregate(pipeline).to_list(length=None)
    
        totals = {"wallet_topup": 0, "game_fee": 0, "winning": 0, "withdrawal": 0}
        for record in result:
            totals[record["_id"]] = record["total_amount"]

        total_transactions = sum(r["count"] for r in result)

        return {
            "total_wallet_topup": totals["wallet_topup"],
            "total_game_fee": totals["game_fee"],
            "total_winning": totals["winning"],
            "total_withdrawal": totals["withdrawal"],
            "total_transactions": total_transactions,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching wallet data: {str(e)}")

@router.get('/user/{user_id}/transactions')
async def get_user_transactions(user_id: str, current_user: dict = Depends(get_current_user)):
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail='Invalid User Id format')
        
        txn_data = user_transaction_db.find({"user_id": ObjectId(user_id)})
        transactions = []
        
        total_wallet_topup = 0
        total_game_fee = 0
        total_winning = 0
        total_withdrawal = 0

        async for txn in txn_data:
            txn['_id'] = str(txn['_id'])
            txn["user_id"] = str(txn["user_id"])
            transactions.append(txn)
            
            if txn['type'] == 'wallet_topup':
                total_wallet_topup += txn['amount']
            elif txn['type'] == 'game_fee':
                total_game_fee += txn['amount']
            elif txn['type'] == 'winning':
                total_winning += txn['amount']
            else:
                total_withdrawal += txn['amount']
        
        summary = {
            "total_wallet_topup": total_wallet_topup,
            "total_game_fee": total_game_fee,
            "total_winning": total_winning,
            "total_withdrawal": total_withdrawal,
            "net_balance": (total_wallet_topup + total_winning) - (total_withdrawal + total_game_fee)
        }

        if not transactions:
            return {"message": "No transactions found for this user", "transactions": []}
        
        return {
            "user_id": user_id,
            "total_transactions": len(transactions),
            "summary": summary,
            "transactions": transactions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")


@router.get("/users_with_txn_summary")
async def get_users_with_txn_summary(current_user: dict = Depends(get_current_user)):
    try:
        pipeline = [
            # 1️⃣ Only non-admin users
            {"$match": {"role": {"$ne": "admin"}}},

            # 2️⃣ Lookup transactions: convert users._id to string to match user_transactions.user_id
            {
                "$lookup": {
                    "from": "user_transactions",
                    "let": {"userId": "$_id"},  # pass ObjectId directly
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$or": [
                                        {"$eq": ["$user_id", "$$userId"]},
                                        {"$eq": [{"$toString": "$user_id"}, {"$toString": "$$userId"}]}
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "transactions"
                }
            },

            # 3️⃣ Calculate totals
            {
                "$addFields": {
                    "total_credit": {
                        "$sum": {
                            "$map": {
                                "input": {
                                    "$filter": {
                                        "input": "$transactions",
                                        "as": "txn",
                                        "cond": {"$eq": [{"$toString": "$$txn.type"}, "wallet_topup"]}
                                    }
                                },
                                "as": "t",
                                "in": "$$t.amount"
                            }
                        }
                    },
                    "total_game_fee": {
                        "$sum": {
                            "$map": {
                                "input": {
                                    "$filter": {
                                        "input": "$transactions",
                                        "as": "txn",
                                        "cond": {"$eq": [{"$toString": "$$txn.type"}, "game_fee"]}
                                    }
                                },
                                "as": "t",
                                "in": "$$t.amount"
                            }
                        }
                    },
                    "total_winning": {
                        "$sum": {
                            "$map": {
                                "input": {
                                    "$filter": {
                                        "input": "$transactions",
                                        "as": "txn",
                                        "cond": {"$eq": [{"$toString": "$$txn.type"}, "winning"]}
                                    }
                                },
                                "as": "t",
                                "in": "$$t.amount"
                            }
                        }
                    },
                    "total_withdrawal": {
                        "$sum": {
                            "$map": {
                                "input": {
                                    "$filter": {
                                        "input": "$transactions",
                                        "as": "txn",
                                        "cond": {"$eq": [{"$toString": "$$txn.type"}, "withdrawal"]}
                                    }
                                },
                                "as": "t",
                                "in": "$$t.amount"
                            }
                        }
                    },
                    # Optional: net balance
                    "net_balance": {
                        "$subtract": [
                            {"$add": ["$total_credit", "$total_winning"]},
                            {"$add": ["$total_withdrawal", "$total_game_fee"]}
                        ]
                    }
                }
            },

            # 4️⃣ Project only required fields
            {
                "$project": {
                    "name": 1,
                    # "email": 1,
                    "mobile_number":1,
                    "created_at": 1,
                    "total_credit": 1,
                    "total_game_fee": 1,
                    "total_winning": 1,
                    "total_withdrawal": 1,
                    "net_balance": 1
                }
            }
        ]

        users = await user_db.aggregate(pipeline).to_list(length=None)

        # Add serial numbers and convert _id to string
        for idx, user in enumerate(users, start=1):
            user["_id"] = str(user["_id"])
            user["sl"] = idx

        return {"data": users, "total_users": len(users)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user summaries: {str(e)}")


@router.get('/todays_earnings')
async def get_todays_earnings(current_user: dict = Depends(get_current_user)):
    try:
        from datetime import datetime, timedelta

        # Calculate start and end of today in UTC
        now = datetime.utcnow()
        start_of_today = datetime(now.year, now.month, now.day)
        start_of_tomorrow = start_of_today + timedelta(days=1)

        pipeline = [
            {
                "$match": {
                    "created_at": {
                        "$gte": start_of_today,
                        "$lt": start_of_tomorrow
                    }
                }
            },
            {
                "$group": {
                    "_id": {"$toString": "$type"},
                    "total_amount": {"$sum": "$amount"},
                    "count": {"$sum": 1}
                }
            }
        ]

        result = await user_transaction_db.aggregate(pipeline).to_list(length=None)

        totals = {"wallet_topup": 0, "game_fee": 0, "winning": 0, "withdrawal": 0}
        for record in result:
            totals[record["_id"]] = record["total_amount"]

        total_transactions = sum(r["count"] for r in result)

        return {
            "total_wallet_topup": totals["wallet_topup"],
            "total_game_fee": totals["game_fee"],
            "total_winning": totals["winning"],
            "total_withdrawal": totals["withdrawal"],
            "total_transactions": total_transactions,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching today's earnings: {str(e)}")
    
@router.get('/monthly_earnings')
async def get_monthly_earnings(
    year: Optional[int] = None,  # If None, use current year
    month: Optional[int] = None,  # If None, return all months
    current_user: dict = Depends(get_current_user)
):
    try:
        from datetime import datetime
        
        # If year not provided, use current year
        if year is None or year == 0:
            year = datetime.utcnow().year
        
        # Validate parameters
        if month is not None and (month < 1 or month > 12):
            raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
        
        # Build match condition
        match_condition = {
            "$expr": {
                "$eq": [{"$year": "$created_at"}, year]
            }
        }
        
        # If specific month requested
        if month:
            match_condition["$expr"] = {
                "$and": [
                    {"$eq": [{"$year": "$created_at"}, year]},
                    {"$eq": [{"$month": "$created_at"}, month]}
                ]
            }
        
        pipeline = [
            {"$match": match_condition},
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"}
                    },
                    "wallet_topup": {
                        "$sum": {
                            "$cond": [
                                {"$eq": [{"$toString": "$type"}, "wallet_topup"]},
                                "$amount",
                                0
                            ]
                        }
                    },
                    "game_fee": {
                        "$sum": {
                            "$cond": [
                                {"$eq": [{"$toString": "$type"}, "game_fee"]},
                                "$amount",
                                0
                            ]
                        }
                    },
                    "winning": {
                        "$sum": {
                            "$cond": [
                                {"$eq": [{"$toString": "$type"}, "winning"]},
                                "$amount",
                                0
                            ]
                        }
                    },
                    "withdrawal": {
                        "$sum": {
                            "$cond": [
                                {"$eq": [{"$toString": "$type"}, "withdrawal"]},
                                "$amount",
                                0
                            ]
                        }
                    },
                    "transaction_count": {"$sum": 1}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "year": "$_id.year",
                    "month": "$_id.month",
                    "wallet_topup": 1,
                    "game_fee": 1,
                    "winning": 1,
                    "withdrawal": 1,
                    "net_earnings": {
                        "$subtract": [
                            {"$add": ["$wallet_topup", "$game_fee"]},
                            {"$add": ["$winning", "$withdrawal"]}
                        ]
                    },
                    "transaction_count": 1
                }
            },
            {"$sort": {"year": 1, "month": 1}}
        ]
        
        result = await user_transaction_db.aggregate(pipeline).to_list(length=None)
        
        # Add month names
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        
        for record in result:
            record["month_name"] = month_names[record["month"] - 1]
        
        return {
            "year": year,
            "month": month,
            "data": result,
            "total_records": len(result)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get('/last_year_earnings')
async def get_last_year_earnings(current_user: dict = Depends(get_current_user)):
    try:
        from datetime import datetime
        
        # Get last year (2024 if current year is 2025)
        current_year = datetime.utcnow().year
        last_year = current_year - 1
        
        # Build match condition for last year
        match_condition = {
            "$expr": {
                "$eq": [{"$year": "$created_at"}, last_year]
            }
        }
        
        pipeline = [
            {"$match": match_condition},
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"}
                    },
                    "wallet_topup": {
                        "$sum": {
                            "$cond": [
                                {"$eq": [{"$toString": "$type"}, "wallet_topup"]},
                                "$amount",
                                0
                            ]
                        }
                    },
                    "game_fee": {
                        "$sum": {
                            "$cond": [
                                {"$eq": [{"$toString": "$type"}, "game_fee"]},
                                "$amount",
                                0
                            ]
                        }
                    },
                    "winning": {
                        "$sum": {
                            "$cond": [
                                {"$eq": [{"$toString": "$type"}, "winning"]},
                                "$amount",
                                0
                            ]
                        }
                    },
                    "withdrawal": {
                        "$sum": {
                            "$cond": [
                                {"$eq": [{"$toString": "$type"}, "withdrawal"]},
                                "$amount",
                                0
                            ]
                        }
                    },
                    "transaction_count": {"$sum": 1}
                }
            },
            {
                "$group": {
                    "_id": "$_id.year",
                    "total_wallet_topup": {"$sum": "$wallet_topup"},
                    "total_game_fee": {"$sum": "$game_fee"},
                    "total_winning": {"$sum": "$winning"},
                    "total_withdrawal": {"$sum": "$withdrawal"},
                    "total_transactions": {"$sum": "$transaction_count"},
                    "monthly_data": {
                        "$push": {
                            "month": "$_id.month",
                            "wallet_topup": "$wallet_topup",
                            "game_fee": "$game_fee",
                            "winning": "$winning",
                            "withdrawal": "$withdrawal",
                            "transaction_count": "$transaction_count"
                        }
                    }
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "year": "$_id",
                    "total_wallet_topup": 1,
                    "total_game_fee": 1,
                    "total_winning": 1,
                    "total_withdrawal": 1,
                    "net_earnings": {
                        "$subtract": [
                            {"$add": ["$total_wallet_topup", "$total_game_fee"]},
                            {"$add": ["$total_winning", "$total_withdrawal"]}
                        ]
                    },
                    "total_transactions": 1,
                    "monthly_data": 1
                }
            }
        ]
        
        result = await user_transaction_db.aggregate(pipeline).to_list(length=None)
        
        # Add month names to monthly data
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        
        if result:
            for month_data in result[0].get("monthly_data", []):
                month_data["month_name"] = month_names[month_data["month"] - 1]
            
            # Sort monthly data by month
            result[0]["monthly_data"] = sorted(result[0]["monthly_data"], key=lambda x: x["month"])
        
        return {
            "last_year": last_year,
            "current_year": current_year,
            "data": result[0] if result else {
                "year": last_year,
                "total_wallet_topup": 0,
                "total_game_fee": 0,
                "total_winning": 0,
                "total_withdrawal": 0,
                "net_earnings": 0,
                "total_transactions": 0,
                "monthly_data": []
            },
            "has_data": len(result) > 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching last year earnings: {str(e)}")


@router.get('/last_month_earnings')
async def get_last_month_earnings(current_user: dict = Depends(get_current_user)):
    try:
        from datetime import datetime, timedelta
        from calendar import monthrange
        
        # Get current date
        now = datetime.utcnow()
        
        # Calculate last month
        if now.month == 1:
            # If current month is January, last month is December of previous year
            last_month = 12
            last_year = now.year - 1
        else:
            last_month = now.month - 1
            last_year = now.year
        
        # Build match condition for last month
        match_condition = {
            "$expr": {
                "$and": [
                    {"$eq": [{"$year": "$created_at"}, last_year]},
                    {"$eq": [{"$month": "$created_at"}, last_month]}
                ]
            }
        }
        
        pipeline = [
            {"$match": match_condition},
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"}
                    },
                    "wallet_topup": {
                        "$sum": {
                            "$cond": [
                                {"$eq": [{"$toString": "$type"}, "wallet_topup"]},
                                "$amount",
                                0
                            ]
                        }
                    },
                    "game_fee": {
                        "$sum": {
                            "$cond": [
                                {"$eq": [{"$toString": "$type"}, "game_fee"]},
                                "$amount",
                                0
                            ]
                        }
                    },
                    "winning": {
                        "$sum": {
                            "$cond": [
                                {"$eq": [{"$toString": "$type"}, "winning"]},
                                "$amount",
                                0
                            ]
                        }
                    },
                    "withdrawal": {
                        "$sum": {
                            "$cond": [
                                {"$eq": [{"$toString": "$type"}, "withdrawal"]},
                                "$amount",
                                0
                            ]
                        }
                    },
                    "transaction_count": {"$sum": 1}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "year": "$_id.year",
                    "month": "$_id.month",
                    "wallet_topup": 1,
                    "game_fee": 1,
                    "winning": 1,
                    "withdrawal": 1,
                    "net_earnings": {
                        "$subtract": [
                            {"$add": ["$wallet_topup", "$game_fee"]},
                            {"$add": ["$winning", "$withdrawal"]}
                        ]
                    },
                    "transaction_count": 1
                }
            }
        ]
        
        result = await user_transaction_db.aggregate(pipeline).to_list(length=None)
        
        # Month names for display
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        
        # Get the number of days in last month
        days_in_last_month = monthrange(last_year, last_month)[1]
        
        # Prepare response
        if result:
            data = result[0]
            data["month_name"] = month_names[last_month - 1]
            data["days_in_month"] = days_in_last_month
        else:
            # No transactions found for last month
            data = {
                "year": last_year,
                "month": last_month,
                "month_name": month_names[last_month - 1],
                "wallet_topup": 0,
                "game_fee": 0,
                "winning": 0,
                "withdrawal": 0,
                "net_earnings": 0,
                "transaction_count": 0,
                "days_in_month": days_in_last_month
            }
        
        return {
            "current_month": now.month,
            "current_year": now.year,
            "current_month_name": month_names[now.month - 1],
            "last_month_data": data,
            "has_data": len(result) > 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching last month earnings: {str(e)}")

