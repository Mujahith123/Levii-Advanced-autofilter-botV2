import motor.motor_asyncio
from info import *
import datetime
import pytz

class Database:

    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.grp = self.db.groups
        self.users = self.db.uersz
        self.req = self.db.requests
        self.misc = self.db.misc
        self.verify_id = self.db.verify_id
        self.movie_requests = self.db.movie_requests
        self.search_logs = self.db.search_logs
        self.scheduled_broadcasts = self.db.scheduled_broadcasts
        # ── New feature collections ──────────────────────────────────────
        self.not_found_logs = self.db.not_found_logs      # Feature 1: content gap
        self.group_activity = self.db.group_activity       # Feature 1: most active groups

    async def find_join_req(self, id):
        return bool(await self.req.find_one({'id': id}))

    async def add_join_req(self, id):
        await self.req.insert_one({'id': id})
    async def del_join_req(self):
        await self.req.drop()

    def new_user(self, id, name):
        return dict(
            id = id,
            name = name,
            joined_date=datetime.datetime.utcnow(),
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
        )


    def new_group(self, id, title):
        return dict(
            id = id,
            title = title,
            chat_status=dict(
                is_disabled=False,
                reason="",
            ),
        )

    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({'id':int(id)})
        return bool(user)

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}})

    async def ban_user(self, user_id, ban_reason="No Reason"):
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_reason=''
        )
        user = await self.col.find_one({'id':int(id)})
        if not user:
            return default
        return user.get('ban_status', default)

    async def get_all_users(self):
        return self.col.find({})


    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})


    async def get_banned(self):
        users = self.col.find({'ban_status.is_banned': True})
        chats = self.grp.find({'chat_status.is_disabled': True})
        b_chats = [chat['id'] async for chat in chats]
        b_users = [user['id'] async for user in users]
        return b_users, b_chats



    async def add_chat(self, chat, title):
        chat = self.new_group(chat, title)
        await self.grp.insert_one(chat)


    async def get_chat(self, chat):
        chat = await self.grp.find_one({'id':int(chat)})
        return False if not chat else chat.get('chat_status')


    async def re_enable_chat(self, id):
        chat_status=dict(
            is_disabled=False,
            reason="",
            )
        await self.grp.update_one({'id': int(id)}, {'$set': {'chat_status': chat_status}})

    async def update_settings(self, id, settings):
        await self.grp.update_one({'id': int(id)}, {'$set': {'settings': settings}})


    async def get_settings(self, id):
        default = {
            'button': SINGLE_BUTTON,
            'botpm': P_TTI_SHOW_OFF,
            'file_secure': PROTECT_CONTENT,
            'imdb': IMDB,
            'spell_check': SPELL_CHECK_REPLY,
            'welcome': MELCOW_NEW_USERS,
            'auto_delete': AUTO_DELETE,
            'auto_ffilter': AUTO_FFILTER,
            'max_btn': MAX_BTN,
            'template': IMDB_TEMPLATE,
            'shortlink': SHORTLINK_URL,
            'shortlink_api': SHORTLINK_API,
            'is_shortlink': IS_SHORTLINK,
            'tutorial': TUTORIAL,
            'is_tutorial': IS_TUTORIAL,
        }
        chat = await self.grp.find_one({'id':int(id)})
        if chat:
            return chat.get('settings', default)
        return default


    async def disable_chat(self, chat, reason="No Reason"):
        chat_status=dict(
            is_disabled=True,
            reason=reason,
            )
        await self.grp.update_one({'id': int(chat)}, {'$set': {'chat_status': chat_status}})


    async def total_chat_count(self):
        count = await self.grp.count_documents({})
        return count


    async def get_all_chats(self):
        return self.grp.find({})


    async def get_db_size(self):
        return (await self.db.command("dbstats"))['dataSize']

    async def get_user(self, user_id):
        user_data = await self.users.find_one({"id": user_id})
        return user_data
    async def update_user(self, user_data):
        await self.users.update_one({"id": user_data["id"]}, {"$set": user_data}, upsert=True)

    async def has_premium_access(self, user_id):
        user_data = await self.get_user(user_id)
        if user_data:
            expiry_time = user_data.get("expiry_time")
            if expiry_time is None:
                # User previously used the free trial, but it has ended.
                return False
            elif isinstance(expiry_time, datetime.datetime) and datetime.datetime.now() <= expiry_time:
                return True
            else:
                await self.users.update_one({"id": user_id}, {"$set": {"expiry_time": None}})
        return False

    async def update_user(self, user_data):
        await self.users.update_one({"id": user_data["id"]}, {"$set": user_data}, upsert=True)

    async def update_one(self, filter_query, update_data):
        try:
            # Assuming self.client and self.users are set up properly
            result = await self.users.update_one(filter_query, update_data)
            return result.matched_count == 1
        except Exception as e:
            print(f"Error updating document: {e}")
            return False

    async def get_expired(self, current_time):
        expired_users = []
        if data := self.users.find({"expiry_time": {"$lt": current_time}}):
#this repo created and maintained by @muja_tg18
            async for user in data:
                expired_users.append(user)
        return expired_users

    async def remove_premium_access(self, user_id):
        return await self.update_one(
            {"id": user_id}, {"$set": {"expiry_time": None}}
        )

    async def check_trial_status(self, user_id):
        user_data = await self.get_user(user_id)
        if user_data:
            return user_data.get("has_free_trial", False)
        return False

    async def give_free_trial(self, user_id):
        #await set_free_trial_status(user_id)
        user_id = user_id
        seconds = 5*60         
        expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
#this repo created and maintained by @muja_tg18
        user_data = {"id": user_id, "expiry_time": expiry_time, "has_free_trial": True}
        await self.users.update_one({"id": user_id}, {"$set": user_data}, upsert=True)

    

    #===================================[ For Dual Verification ]================================#
    async def get_verify_user(self, user_id):
        user_id = int(user_id)

        user = await self.misc.find_one({"user_id": user_id})
        ist_timezone = pytz.timezone(TIMEZONE)

        if not user:
            res = {
                "user_id": user_id,
                "last_verified": datetime.datetime(2020, 5, 17, 0, 0, 0, tzinfo=ist_timezone),
                "second_time_verified": datetime.datetime(2019, 5, 17, 0, 0, 0, tzinfo=ist_timezone),
            }

            user = await self.misc.insert_one(res)
            user = await self.misc.find_one({"user_id": user_id})
        return user

    async def update_verify_user(self, user_id, value:dict):
        user_id = int(user_id)
        myquery = {"user_id": user_id}
        newvalues = {"$set": value}
        return await self.misc.update_one(myquery, newvalues)

    async def is_user_verified(self, user_id):
        user = await self.get_verify_user(user_id)

        try:
            pastDate = user["last_verified"]
        except Exception:
            user = await self.get_verify_user(user_id)
            pastDate = user["last_verified"]

        ist_timezone = pytz.timezone(TIMEZONE)
        pastDate = pastDate.astimezone(ist_timezone)
        current_time = datetime.datetime.now(tz=ist_timezone)

        seconds_since_midnight = (current_time - datetime.datetime(current_time.year, current_time.month, current_time.day, 0, 0, 0, tzinfo=ist_timezone)).total_seconds()

        # Calculate the difference between the two times
        time_diff = current_time - pastDate

        # Get the total number of seconds between the two times
        total_seconds = time_diff.total_seconds()
        return total_seconds <= seconds_since_midnight

    async def use_second_shortener(self, user_id):
        user = await self.get_verify_user(user_id)
        if not user.get("second_time_verified"):
            ist_timezone = pytz.timezone(TIMEZONE)
            await self.update_verify_user(user_id, {"second_time_verified":datetime.datetime(2019, 5, 17, 0, 0, 0, tzinfo=ist_timezone)})
            user = await self.get_verify_user(user_id)

        if await self.is_user_verified(user_id):
            try:
                pastDate = user["last_verified"]
            except Exception:
                user = await self.get_verify_user(user_id)
                pastDate = user["last_verified"]

            ist_timezone = pytz.timezone(TIMEZONE)
            pastDate = pastDate.astimezone(ist_timezone)
            current_time = datetime.datetime.now(tz=ist_timezone)
            time_difference = current_time - pastDate
            if time_difference > datetime.timedelta(seconds=VERIFY_TIME2):
                pastDate = user["last_verified"].astimezone(ist_timezone)
                second_time = user["second_time_verified"].astimezone(ist_timezone)
                return second_time < pastDate
        return False

    async def create_verify_id(self, user_id: int, hash):
        res = {"user_id": user_id, "hash":hash, "verified":False}
        return await self.verify_id.insert_one(res)

    async def get_verify_id_info(self, user_id: int, hash):
        return await self.verify_id.find_one({"user_id": user_id, "hash": hash})

    async def update_verify_id_info(self, user_id, hash, value: dict):
        myquery = {"user_id": user_id, "hash": hash}
        newvalues = { "$set": value }
        return await self.verify_id.update_one(myquery, newvalues)

    #===================================[ Auto Request Notify ]================================#
    async def add_movie_request(self, user_id, query):
        """Save a /request so we can notify the user once a matching file is indexed."""
        await self.movie_requests.insert_one({
            "user_id": int(user_id),
            "query": query.strip(),
            "requested_at": datetime.datetime.utcnow(),
            "notified": False,
        })

    async def get_open_requests(self):
        """All requests not yet matched to an indexed file."""
        return self.movie_requests.find({"notified": False})

    async def mark_request_notified(self, request_id):
        await self.movie_requests.update_one({"_id": request_id}, {"$set": {"notified": True}})

    #===================================[ Referral System ]================================#
    async def set_referrer(self, user_id, referrer_id):
        """Record who referred this user, once only. Returns True the first time it's set."""
        user_id, referrer_id = int(user_id), int(referrer_id)
        if user_id == referrer_id:
            return False
        user = await self.col.find_one({'id': user_id})
        if user and user.get('referred_by'):
            return False
        await self.col.update_one({'id': user_id}, {'$set': {'referred_by': referrer_id}}, upsert=True)
        return True

    async def add_referral_credit(self, referrer_id, reward_days=1):
        """Bump the referrer's referral_count and stack `reward_days` of premium on top of any existing plan."""
        referrer_id = int(referrer_id)
        await self.col.update_one({'id': referrer_id}, {'$inc': {'referral_count': 1}}, upsert=True)
        user_data = await self.get_user(referrer_id)
        now = datetime.datetime.now()
        base = now
        if user_data and user_data.get("expiry_time") and user_data["expiry_time"] > now:
            base = user_data["expiry_time"]
        new_expiry = base + datetime.timedelta(days=reward_days)
        await self.update_user({"id": referrer_id, "expiry_time": new_expiry})
        return new_expiry

    async def get_referral_count(self, user_id):
        user = await self.col.find_one({'id': int(user_id)})
        return user.get('referral_count', 0) if user else 0

    #===================================[ Stats Dashboard ]================================#
    async def log_search(self, query):
        if not query or not query.strip():
            return
        await self.search_logs.insert_one({
            "query": query.strip().lower(),
            "ts": datetime.datetime.utcnow(),
        })

    @staticmethod
    def _midnight_ist_as_utc():
        ist = pytz.timezone(TIMEZONE)
        now_ist = datetime.datetime.now(ist)
        midnight_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight_ist.astimezone(pytz.utc).replace(tzinfo=None)

    async def get_today_search_count(self):
        return await self.search_logs.count_documents({"ts": {"$gte": self._midnight_ist_as_utc()}})

    async def get_top_searches(self, limit=5):
        """Most searched queries of all time, as [(query, count), ...]."""
        pipeline = [
            {"$group": {"_id": "$query", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ]
        return [(doc["_id"], doc["count"]) async for doc in self.search_logs.aggregate(pipeline)]

    async def get_new_users_today_count(self):
        return await self.col.count_documents({"joined_date": {"$gte": self._midnight_ist_as_utc()}})

    #===================================[ Scheduled Broadcast ]================================#
    async def add_scheduled_broadcast(self, chat_id, message_id, scheduled_time, created_by):
        result = await self.scheduled_broadcasts.insert_one({
            "chat_id": int(chat_id),
            "message_id": int(message_id),
            "scheduled_time": scheduled_time,
            "created_by": int(created_by),
            "status": "pending",
        })
        return result.inserted_id

    async def get_pending_scheduled_broadcasts(self):
        return [doc async for doc in self.scheduled_broadcasts.find({"status": "pending"})]

    async def mark_broadcast_status(self, broadcast_id, status):
        await self.scheduled_broadcasts.update_one({"_id": broadcast_id}, {"$set": {"status": status}})

    # ══════════════════════════════════════════════════════════════════
    #  Feature 1 – Content Gap Analytics
    # ══════════════════════════════════════════════════════════════════

    async def log_not_found(self, query, user_id=None, group_id=None, group_title=None):
        """Log a search that returned zero results (content gap tracking)."""
        if not query or not query.strip():
            return
        q = query.strip().lower()
        await self.not_found_logs.insert_one({
            "query": q,
            "user_id": user_id,
            "group_id": group_id,
            "group_title": group_title,
            "ts": datetime.datetime.utcnow(),
        })

    async def get_top_not_found(self, limit=10):
        """Most searched-but-not-found queries — [(query, count), ...]."""
        pipeline = [
            {"$group": {"_id": "$query", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ]
        return [(doc["_id"], doc["count"]) async for doc in self.not_found_logs.aggregate(pipeline)]

    async def log_group_activity(self, group_id, group_title):
        """Increment search count for a group (upsert)."""
        if not group_id:
            return
        await self.group_activity.update_one(
            {"group_id": group_id},
            {"$inc": {"count": 1}, "$set": {"title": group_title or str(group_id)}},
            upsert=True,
        )

    async def get_top_active_groups(self, limit=5):
        """Groups with most searches — [(title, group_id, count), ...]."""
        pipeline = [
            {"$sort": {"count": -1}},
            {"$limit": limit},
            {"$project": {"title": 1, "group_id": 1, "count": 1}},
        ]
        return [
            (doc.get("title", str(doc["group_id"])), doc["group_id"], doc["count"])
            async for doc in self.group_activity.aggregate(pipeline)
        ]

    async def get_search_trend(self, days=7, limit=10):
        """Top searches in the last `days` days — [(query, count), ...]."""
        since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        pipeline = [
            {"$match": {"ts": {"$gte": since}}},
            {"$group": {"_id": "$query", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ]
        return [(doc["_id"], doc["count"]) async for doc in self.search_logs.aggregate(pipeline)]

    async def get_today_not_found_count(self):
        return await self.not_found_logs.count_documents({"ts": {"$gte": self._midnight_ist_as_utc()}})

    # ══════════════════════════════════════════════════════════════════
    #  Feature 4 – Recently Added Movies (indexed in ia_filterdb, but
    #              we expose a helper here for convenience)
    # ══════════════════════════════════════════════════════════════════
    # (Actual query lives in ia_filterdb.get_recent_files; nothing extra
    #  needed in this class.)


db = Database(DATABASE_URI, DATABASE_NAME)
