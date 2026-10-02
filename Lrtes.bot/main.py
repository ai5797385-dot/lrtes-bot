import os
from threading import Thread

# --- Ավելացրեք այս հատվածը ֆայլի սկզբում ---
from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running!"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# Գործարկում ենք սերվերը առանձին թրեդով
Thread(target=run_web).start()
# ---------------------------------------------

# Այստեղ սկսվում է ձեր բոտի կոդը (օրինակ՝ bot.infinity_polling(), asyncio.run(main()) և այլն)
# ... ձեր մնացած կոդը ...
import asyncio
import os
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from google import genai

# --- ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ ---
BOT_TOKEN = "8929284091:AAFCK5Ke67z6Pciwuo6qYGJ91DBaGhwx7sE"
GEMINI_API_KEY = "gemini app key"
REAL_ADMIN_ID = 6614409372  # ⚠️️ Գրեք ձեր իրական Telegram-ի User ID-ն (թիվով)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Հիշողության կառուցվածք
active_games = {}  # chat_id -> game_data dict
banned_users = set()  # Արգելափակված օգտատերերի ID-ներ
global_bot_theme = "normal"  # normal, valentine, newyear, halloween

# Տոնական ոճերի կարգավորումներ
THEMES = {
    "normal": {
        "title": "🕵️ Լրտես",
        "spy_name": "Լրտես",
        "spy_emoji": "🕵️",
        "intro": "Լրտեսը քեզ է սպասում, միացիր խաղին!",
    },
    "valentine": {
        "title": "💘 Սուրբ Վալենտին",
        "spy_name": "Վալենտին (Գաղտնի սիրահար)",
        "spy_emoji": "💘",
        "intro": " Cupid-ի սլաքն ուղղված է դեպի քեզ, միացիր սիրային խաղին! 💖",
    },
    "newyear": {
        "title": "🎄 Նոր Տարի",
        "spy_name": "Ձմեռ պապիկ",
        "spy_emoji": "🎅",
        "intro": "🎁 Նվերների ժամանակն է, միացիր Ամանորյա Լրտես խաղին! ❄️",
    },
    "halloween": {
        "title": "🎃 Հելոուին",
        "spy_name": "Զոմբի",
        "spy_emoji": "🧟‍♂️",
        "intro": "👻 Ուրվականները արթնացել են, միացիր Հելոուինի խաղին! 🎃",
    },
}


def get_ai_word(theme: str) -> str:
    """Գեներացնում է բառ Gemini-ի միջոցով՝ հաշվի առնելով թեման"""
    prompt_map = {
        "normal": (
            "Գրիր մեկ հայերեն առարկա, վայր կամ հասկացություն Լրտես խաղի համար։"
            " Ուղարկիր ՄԻԱՅՆ բառը՝ առանց հավելյալ տեքստի:"
        ),
        "valentine": (
            "Գրիր սիրո, սրտի, նվերի կամ ռոմանտիկ թեմայով մեկ հայերեն բառ Լրտես"
            " խաղի համար։ Ուղարկիր ՄԻԱՅՆ բառը:"
        ),
        "newyear": (
            "Գրիր Ամանորի կամ ձմեռային թեմայով մեկ հայերեն բառ Լրտես խաղի"
            " համար։ Ուղարկիր ՄԻԱՅՆ բառը:"
        ),
        "halloween": (
            "Գրիր Հելոուինի, սարսափի կամ առեղծվածային թեմայով մեկ հայերեն բառ"
            " Լրտես խաղի համար։ Ուղարկիր ՄԻԱՅՆ բառը:"
        ),
    }
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_map.get(theme, prompt_map["normal"]),
        )
        return response.text.strip()
    except Exception:
        fallback_words = [
            "Հիվանդանոց",
            "Օդանավակայան",
            "Թատրոն",
            "Համալսարան",
            "Սուպերմարկետ",
        ]
        return random.choice(fallback_words)


# --- 1. /START ՀՐԱՄԱՆ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
  kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="➕ Ավելացնել բոտը սեփական չատում",
                  url=f"https://t.me/{(await message.bot.me()).username}?startgroup=true",
              )
          ]
      ]
  )
  text = (
      "👋 Բարև ձեզ: Սա «Լրտես» (Spy) հետաքրքրաշարժ խաղ-բոտն է։\n\nԱվելացրեք բոտը"
      " ձեր խմբային չատում, ադմինիստրատոր դարձրեք և խմբում գրեք /game խաղը"
      " սկսելու համար։"
  )
  await message.answer(text, reply_markup=kb)


# --- 2. ԹՈՆԱԿԱՆ ԵՎ ԱԴՄԻՆԻ ՀՐԱՄԱՆՆԵՐ ---
@dp.message(Command("valentine", "newyear", "hellowin", "normal", "ban", "unban"))
async def admin_and_theme_commands(message: types.Message):
  global global_bot_theme

  user_id = message.from_user.id
  command = message.text.split()[0].replace("/", "")

  # Ստուգում ենք՝ արդյոք օգտատերը բոտի իրական ադմինն է
  if user_id != REAL_ADMIN_ID:
    await message.answer("❌ Այս հրամանները նախատեսված են միայն բոտի ադմինի համար։")
    return

  # Թեմաների փոփոխություն
  if command in ["valentine", "newyear", "hellowin", "normal"]:
    theme_key = "halloween" if command == "hellowin" else command
    global_bot_theme = theme_key
    theme_info = THEMES[global_bot_theme]
    await message.answer(
        f"🎨 Բոտի թեման փոխվեց!\nՆոր թեմա՝ **{theme_info['title']}** {theme_info['spy_emoji']}"
    )
    return

  # /ban և /unban հրամաններ
  args = message.text.split()
  if len(args) < 2:
    await message.answer(
        "⚠️ Խնդրում եմ նշեք օգտատիրոջ Username-ը կամ User ID-ն: (Օրինակ՝"
        f" /{command} 12345678)"
    )
    return

  target = args[1].replace("@", "")

  # Եթե User ID է (թիվ է)
  if target.isdigit():
    target_id = int(target)
    if command == "ban":
      banned_users.add(target_id)
      await message.answer(f"🚫 Օգտատեր (ID: {target_id}) արգելափակվեց։")
    else:
      banned_users.discard(target_id)
      await message.answer(f"✅ Օգտատեր (ID: {target_id}) ապաբլոկավորվեց։")
  else:
    # Եթե username-ով է (նշում ենք տեղեկատվական հաղորդագրություն)
    await message.answer(
        f"ℹ️ Username-ով արգելափակման համար ավելի հարմար է օգտագործել User ID-ն:"
        f" Նշված թիրախը՝ @{target}"
    )


# --- 3. /GAME ՀՐԱՄԱՆ (ԽԱՂԻ ՍԿԻԶԲ) ---
@dp.message(Command("game"))
async def cmd_game(message: types.Message):
  if message.chat.type == "private":
    await message.answer("⚠️ Այս հրամանը նախատեսված է միայն խմբային չատերի համար։")
    return

  user_id = message.from_user.id
  if user_id in banned_users:
    await message.answer("❌ Դուք արգելափակված եք այս բոտում։")
    return

  chat_id = message.chat.id
  if chat_id in active_games:
    await message.answer("⚠️ Այս չատում արդեն կա ընթացող կամ սպասվող խաղ։")
    return

  theme_info = THEMES[global_bot_theme]

  active_games[chat_id] = {
      "host_id": user_id,
      "players": {},  # user_id -> full_name
      "paid_players": set(),
      "time_left": 300,  # 5 րոպե
      "max_free": 12,
      "max_paid": 8,
      "status": "waiting",
      "theme": global_bot_theme,
  }

  await update_lobby_message(chat_id, message.bot)


async def update_lobby_message(chat_id: int, bot_instance: Bot):
  game = active_games.get(chat_id)
  if not game:
    return

  theme_info = THEMES[game["theme"]]
  total_players = len(game["players"])
  minutes_left = game["time_left"] // 60

  text = (
      f"{theme_info['spy_emoji']} **{theme_info['intro']}**\n\n"
      f"👥 Միացած խաղացողներ ({total_players}/20):\n"
  )
  for uid, name in game["players"].items():
    paid_mark = " ⭐️" if uid in game["paid_players"] else ""
    text += f"• {name}{paid_mark}\n"

  text += f"\n⏳ Մնացած ժամանակը՝ **{minutes_left} րոպե**\n"
  if total_players >= 12:
    text += (
        "⚠️ Անվճար տեղերը վերջացել են: Հաջորդ 8 տեղերը վճարովի են (5 Stars) ⭐️"
    )

  kb_buttons = [
      [InlineKeyboardButton(text="🎮 Միանալ խաղին", callback_data="join_game")],
      [
          InlineKeyboardButton(
              text="➕ Ավելացնել ժամանակ (+1 րոպե)", callback_data="add_time"
          )
      ],
      [
          InlineKeyboardButton(
              text="🚀 Սկսել խաղը հիմա", callback_data="start_game_now"
          )
      ],
  ]
  if total_players > 12:
    kb_buttons.insert(
        1,
        [
            InlineKeyboardButton(
                text="⭐️ Միանալ վճարով (5 Stars)", callback_data="join_paid"
            )
        ],
    )

  markup = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
  msg = await bot_instance.send_message(chat_id, text, reply_markup=markup)
  game["lobby_msg_id"] = msg.message_id

  asyncio.create_task(lobby_timer(chat_id, bot_instance))


async def lobby_timer(chat_id: int, bot_instance: Bot):
  while chat_id in active_games and active_games[chat_id]["status"] == "waiting":
    await asyncio.sleep(60)
    if chat_id not in active_games:
      break
    game = active_games[chat_id]
    game["time_left"] -= 60

    if game["time_left"] <= 0:
      await start_actual_game(chat_id, bot_instance)
      break
    else:
      mins = game["time_left"] // 60
      try:
        await bot_instance.send_message(
            chat_id,
            f"⏳ Ուշադրություն: Խաղին միանալու համար մնացել է մոտ {mins} րոպե:",
        )
      except Exception:
        pass


# --- 4. ԿՈՃԱԿՆԵՐԻ ՄՇԱԿՈՒՄ (JOIN / TIME / START) ---
@dp.callback_query(
    F.data.in_(["join_game", "join_paid", "add_time", "start_game_now"])
)
async def callback_handler(call: types.CallbackQuery):
  chat_id = call.message.chat.id
  user_id = call.from_user.id
  user_name = call.from_user.full_name

  if user_id in banned_users:
    await call.answer("❌ Դուք արգելափակված եք բոտից:", show_alert=True)
    return

  if chat_id not in active_games:
    await call.answer("Խաղն արդեն ավարտվել է կամ գոյություն չունի:", show_alert=True)
    return

  game = active_games[chat_id]

  if call.data == "join_game":
    if len(game["players"]) >= 20:
      await call.answer(
          "❌ Խաղը լցված է (առավելագույնը 20 մասնակից):", show_alert=True
      )
      return
    if user_id in game["players"]:
      await call.answer("⚠️ Դուք արդեն միացել եք խաղին:", show_alert=True)
      return
    if len(game["players"]) >= game["max_free"]:
      await call.answer(
          "⚠️ Անվճար տեղերը սպառվել են: Օգտագործեք վճարովի կոճակը (5 Stars):",
          show_alert=True,
      )
      return

    game["players"][user_id] = user_name
    await call.answer("✅ Դուք հաջողությամբ միացաք խաղին:")

  elif call.data == "join_paid":
    if len(game["players"]) >= 20:
      await call.answer("❌ Խաղը լցված է:", show_alert=True)
      return
    if user_id in game["players"]:
      await call.answer("⚠️ Դուք արդեն միացել եք խաղին:", show_alert=True)
      return
    if len(game["players"]) < game["max_free"]:
      await call.answer(
          "⚠️ Անվճար տեղեր դեռ կան, կարող եք միանալ անվճար:", show_alert=True
      )
      return

    prices = [LabeledPrice(label="Վճարովի տեղ Լրտես խաղում", amount=5)]
    await call.message.answer_invoice(
        title="Լրտես խաղի վճարովի տեղ",
        description="Վճարեք 5 Stars խաղին միանալու համար (12+ մասնակից):",
        payload=f"join_paid_game_{chat_id}",
        provider_token="",
        currency="XTR",
        prices=prices,
    )
    return

  elif call.data == "add_time":
    member = await bot.get_chat_member(chat_id, user_id)
    if (
        user_id != game["host_id"]
        and member.status not in ["creator", "administrator"]
        and user_id != REAL_ADMIN_ID
    ):
      await call.answer(
          "❌ Միայն խաղը սկսողը կամ ադմինը կարող են ժամանակ ավելացնել:",
          show_alert=True,
      )
      return

    if game["time_left"] < 600:
      game["time_left"] += 60
      await call.answer("➕ Ավելացվեց 1 րոպե:")
    else:
      await call.answer("⚠️ Առավելագույն ժամանակը 10 րոպե է:", show_alert=True)
      return

  elif call.data == "start_game_now":
    member = await bot.get_chat_member(chat_id, user_id)
    if (
        user_id != game["host_id"]
        and member.status not in ["creator", "administrator"]
        and user_id != REAL_ADMIN_ID
    ):
      await call.answer(
          "❌ Միայն խաղը սկսողը կամ ադմինը կարող են սկսել խաղը:", show_alert=True
      )
      return

    if len(game["players"]) < 3:
      await call.answer(
          "❌ Խաղի համար անհրաժեշտ է նվազագույնը 3 մասնակից:", show_alert=True
      )
      return

    await start_actual_game(chat_id, call.bot)
    return


@dp.pre_checkout_query(F.payload.startswith("join_paid_game_"))
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
  await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
  payload = message.successful_payment.invoice_payload
  chat_id = int(payload.split("_")[-1])
  user_id = message.from_user.id
  user_name = message.from_user.full_name

  if chat_id in active_games:
    game = active_games[chat_id]
    if len(game["players"]) < 20:
      game["players"][user_id] = user_name
      game["paid_players"].add(user_id)
      await message.answer(
          "🎉 Վճարումը հաջողվեց: Դուք հաջողությամբ միացաք խաղին ⭐️"
      )


# --- 5. ԽԱՂԻ ՄԵԿՆԱՐԿ ԵՎ ԲԱՌԵՐԻ ԲԱՇԽՈՒՄ ---
async def start_actual_game(chat_id: int, bot_instance: Bot):
  game = active_games.get(chat_id)
  if not game or game["status"] == "playing":
    return
  game["status"] = "playing"

  players = list(game["players"].keys())
  total_p = len(players)

  if total_p < 3:
    await bot_instance.send_message(
        chat_id, "❌ Մասնակիցների քիչ լինելու պատճառով խաղը չեղարկվեց:"
    )
    del active_games[chat_id]
    return

  if 5 <= total_p <= 8:
    num_spies = 2
  elif total_p >= 9:
    num_spies = 3
  else:
    num_spies = 1

  spies = random.sample(players, num_spies)
  secret_word = get_ai_word(game["theme"])
  theme_info = THEMES[game["theme"]]

  game["secret_word"] = secret_word
  game["spies"] = spies
  game["players_list"] = players

  for uid in players:
    try:
      if uid in spies:
        await bot_instance.send_message(
            uid,
            f"🚨 **ԴՈՒՔ {theme_info['spy_name'].upper()} ԵՔ!**"
            f" {theme_info['spy_emoji']} Փորձեք գուշակել բառը՝ առանց մատնվելու:",
        )
      else:
        await bot_instance.send_message(
            uid,
            f"🤫 Գաղտնի բառը՝ **{secret_word}**\nՈւշադիր եղեք, մի՛ ասեք բառը"
            " ուղղակիորեն։",
        )
    except Exception:
      pass

  await bot_instance.send_message(
      chat_id,
      f"{theme_info['spy_emoji']} **Խաղը սկսվեց!** ({theme_info['title']})"
      " Մասնակիցները ստացան իրենց դերերը:",
  )

  try:
    for uid in players:
      await bot_instance.restrict_chat_member(
          chat_id,
          uid,
          permissions=types.ChatPermissions(can_send_messages=False),
      )
    await bot_instance.send_message(
        chat_id,
        "🔇 Չատը ժամանակավորապես արգելափակվեց (Mute): Հերթով բոլորը պետք է ասեն"
        " 1-ական բառ:",
    )
  except Exception:
    await bot_instance.send_message(
        chat_id,
        "⚠️ Տվեք բոտին ադմինիստրատորի իրավունքներ (մարդկանց Mute անելու համար):",
    )

  asyncio.create_task(run_word_rounds(chat_id, bot_instance))


async def run_word_rounds(chat_id: int, bot_instance: Bot):
  game = active_games[chat_id]
  players = game["players_list"]

  for round_num in range(1, 4):
    await bot_instance.send_message(
        chat_id,
        f"🗣️ **ՓՈՒԼ #{round_num}**: Հերթով գրեք բառեր, որոնք կապ ունեն գաղտնի"
        " բառի հետ:",
    )
    for uid in players:
      name = game["players"][uid]
      await bot_instance.send_message(
          chat_id, f"👉 Այժմ **{name}**-ը պետք է ասի մի բառ:"
      )
      await asyncio.sleep(15)

  await bot_instance.send_message(
      chat_id, "🛑 Բոլոր շանսերն սպառվեցին: Անցնում ենք քվեարկության փուլին:"
  )

  try:
    for uid in players:
      await bot_instance.restrict_chat_member(
          chat_id,
          uid,
          permissions=types.ChatPermissions(
              can_send_messages=True,
              can_send_media_messages=True,
              can_send_other_messages=True,
          ),
      )
  except Exception:
    pass

  await start_voting_phase(chat_id, bot_instance)


# --- 6. ՔՎԵԱՐԿՈՒԹՅԱՆ ՓՈՒԼ ---
async def start_voting_phase(chat_id: int, bot_instance: Bot):
  game = active_games[chat_id]
  game["status"] = "voting"
  game["votes"] = {}

  spies = game["spies"]
  current_spy_index = 0
  game["current_spy_index"] = current_spy_index

  await prompt_vote(chat_id, bot_instance, spies[current_spy_index], 1)


async def prompt_vote(
    chat_id: int, bot_instance: Bot, target_spy_id: int, spy_number: int
):
  game = active_games[chat_id]
  players = game["players_list"]

  kb_buttons = []
  for uid in players:
    if uid != target_spy_id:
      kb_buttons.append([
          InlineKeyboardButton(
              text=game["players"][uid], callback_data=f"vote_{uid}"
          )
      ])

  markup = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
  await bot_instance.send_message(
      chat_id,
      f"🗳️ **ՔՎԵԱՐԿՈՒԹՅՈՒՆ #{spy_number}**\nՈ՞վ է ձեր կարծիքով լրտեսը? Սեղմեք"
      " կոճակը:",
      reply_markup=markup,
  )


@dp.callback_query(F.data.startswith("vote_"))
async def handle_vote(call: types.CallbackQuery):
  chat_id = call.message.chat.id
  user_id = call.from_user.id

  if chat_id not in active_games:
    await call.answer("Խաղն ավարտված է:", show_alert=True)
    return

  game = active_games[chat_id]
  if user_id not in game["players"]:
    await call.answer("❌ Դուք այս խաղի մասնակից չեք:", show_alert=True)
    return

  voted_for = int(call.data.split("_")[1])
  game["votes"][user_id] = voted_for
  await call.answer("✅ Ձեր քվեն ընդունվեց:")

  if len(game["votes"]) >= len(game["players"]):
    await process_voting_result(chat_id, call.bot)


async def process_voting_result(chat_id: int, bot_instance: Bot):
  game = active_games[chat_id]
  votes = game["votes"]
  theme_info = THEMES[game["theme"]]

  vote_counts = {}
  for v_for in votes.values():
    vote_counts[v_for] = vote_counts.get(v_for, 0) + 1

  if not vote_counts:
    return

  suspect = max(vote_counts, key=vote_counts.get)
  suspect_name = game["players"].get(suspect, "Անհայտ")

  spies = game["spies"]
  current_idx = game["current_spy_index"]
  current_target_spy = spies[current_idx]

  if suspect == current_target_spy:
    await bot_instance.send_message(
        chat_id,
        f"🎯 Ճիշտ է: **{suspect_name}**-ը {theme_info['spy_name']} էր!",
    )
    game["current_spy_index"] += 1

    if game["current_spy_index"] < len(spies):
      await bot_instance.send_message(
          chat_id,
          "🔄 Կա ևս մեկը: Յուրաքանչյուրդ ստանում եք ևս 2 բառ ասելու շանս:",
      )
      game["votes"] = {}
      await prompt_vote(
          chat_id,
          bot_instance,
          spies[game["current_spy_index"]],
          game["current_spy_index"] + 1,
      )
    else:
      await bot_instance.send_message(
          chat_id,
          f"🏆 **ՀԱՂԹԱՆԱԿ!** Մասնակիցները հաջողությամբ գտան բոլոր"
          f" {theme_info['spy_name']}ներին։",
      )
      end_game_cleanup(chat_id)
  else:
    spies_names = ", ".join(
        [game["players"][s] for s in spies if s in game["players"]]
    )
    await bot_instance.send_message(
        chat_id,
        f"❌ **ՍԽԱЛЬ ՔՎԵԱՐԿՈՒԹՅՈՒՆ**\n{suspect_name}-ը հասարակ խաղացող"
        f" էր:\n\n🕵️ **Հաղթեցին {theme_info['spy_name']}ները!** Նրանք էին՝"
        f" **{spies_names}**",
    )
    end_game_cleanup(chat_id)


def end_game_cleanup(chat_id: int):
  if chat_id in active_games:
    del active_games[chat_id]


# --- ԲՈՏԻ ԳՈՐԾԱՐԿՈՒՄ ---
async def main():
  print("Բոտը աշխատում է տոնական ռեժիմներով և ադմինիստրատորի հրամաններով...")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
