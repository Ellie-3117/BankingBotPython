import requests, json, os, sqlite3
from discord import *
from discord.ext import commands
from urllib.parse import quote
from datetime import datetime
bot=commands.Bot(command_prefix="bk!",intents=Intents.all())
with open('bank.json', 'r', encoding='utf-8') as f:
    language_dict = json.load(f)
conn = sqlite3.connect('commands.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS banking (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id TEXT,
                 user_name TEXT,
                 guild_name TEXT,
                 bank_name TEXT,
                 bank_id TEXT,
                 account_name TEXT,
                 account_no TEXT,
                 amount TEXT,
                 description TEXT,
                 template TEXT,
                 timestamp TEXT,
                 command_text TEXT
             )''')
conn.commit()

data = sqlite3.connect('user.db')
user_access = data.cursor()
user_access.execute('''CREATE TABLE IF NOT EXISTS user (
    user_id TEXT PRIMARY KEY,
    time TEXT
)''')
data.commit()
EXEMPT_USER_ID = 1002018505601863730
class BankingBot(commands.Cog):
    def __init__(self,bot):
        self.bot=bot
    @app_commands.command(name='thêm_mem', description="Thêm thành viên")
    @app_commands.user_install()
    @app_commands.guild_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True) 
    async def add_member(self,interaction:Interaction, user_id: str, time: str):
        if interaction.user.id != EXEMPT_USER_ID:  
            await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này.")
            return

        try:
            expiration_date = datetime.strptime(time, "%d/%m/%Y")
            user_access.execute("INSERT OR REPLACE INTO user (user_id, time) VALUES (?, ?)", (user_id, expiration_date.isoformat()))
            data.commit()
            await interaction.response.send_message(f"Thành viên {user_id} đã được thêm với thời hạn {time}.")
        except Exception as e:
            await interaction.response.send_message(f"Đã xảy ra lỗi: {e}")


    def is_member_active(self,user_id: str) -> bool:
        if user_id == EXEMPT_USER_ID: 
            return True

        user_access.execute("SELECT time FROM user WHERE user_id = ?", (user_id,))
        result = user_access.fetchone()

        if result:
            expiration_date = datetime.fromisoformat(result[0])
            if datetime.now() <= expiration_date:
                return True
        return False

    @app_commands.command(name="kiểm_tra_tài_khoản", description='Kiểm tra bạn đã quá hạn hay chưa')
    @app_commands.user_install()
    @app_commands.guild_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True) 
    async def check_expiration(self,interaction:Interaction):
        user_id = interaction.user.id

        if user_id == EXEMPT_USER_ID:
            await interaction.response.send_message("Tài khoản của bạn không có hạn sử dụng.")
            return

        await interaction.response.defer()

        user_access.execute("SELECT time FROM user WHERE user_id = ?", (user_id,))
        result = user_access.fetchone()

        if result:
            expiration_date = datetime.fromisoformat(result[0])
            if datetime.now() > expiration_date:
                await interaction.followup.send("Tài khoản của bạn đã hết hạn. Vui lòng liên hệ admin để gia hạn.")
            else:
                days_left = (expiration_date - datetime.now()).days
                await interaction.followup.send(f"Tài khoản của bạn còn {days_left} ngày trước khi hết hạn.")
        else:
            await interaction.followup.send("Tài khoản của bạn không tồn tại trong hệ thống.")

    async def check_permissions(self,interaction:Interaction):
        if interaction.user.id == EXEMPT_USER_ID:
            return True

        if not self.is_member_active(interaction.user.id):
            await interaction.response.send_message("Tài khoản của bạn đã hết hạn hoặc không có quyền truy cập. Vui lòng liên hệ admin.")
            return False
        return True

    def log_command_to_db(self,table: str, data: dict):
        keys = ', '.join(data.keys())
        question_marks = ', '.join(['?'] * len(data))
        query = f'INSERT INTO {table} ({keys}) VALUES ({question_marks})'
        c.execute(query, tuple(data.values()))
        conn.commit()
    

    @app_commands.choices(option_create=[
        app_commands.Choice(name="Chỉ Qr", value="qr_only"),
        app_commands.Choice(name="QR và Ngân Hàng", value='compact'),
        app_commands.Choice(name="QR,Ngân hàng,stk,số tiền", value="compact2"),
        app_commands.Choice(name="Full", value="print")])
    @app_commands.choices(
        banking=[app_commands.Choice(name=bank, value=str(code)) for bank, code in language_dict.items()])
    @app_commands.command(name='tạo_mã_qr_banking', description="Toạ mã QR banking")
    @app_commands.user_install()
    @app_commands.guild_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True) 
    async def bank(self,interaction:Interaction, banking: app_commands.Choice[str], option_create: app_commands.Choice[str], namestk: str, stk: str, sotien: str, save: bool = False, descrition: str = None, command_text: str = None):
        if not await self.check_permissions(interaction):
            return
        bank_id = banking.value
        template = option_create.value
        des = descrition if descrition else interaction.guild.name
        account_no = str(stk)
        description = des.replace(" ", "%20")
        account_name = namestk.replace(" ", "%20")
        qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-{template}.png?amount={sotien}&addInfo={description}&accountName={account_name}"

        if qr_url.startswith("https://img.vietqr.io/image/"):
            embed = Embed(
                title="QR Code",
                description="Chuyển Khoản Nhanh.",
                color=Color.random()
            )
            bot_avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
            embed.set_author(name=interaction.user.display_name, icon_url=bot_avatar_url)
            embed.set_thumbnail(url=bot_avatar_url)
            embed.add_field(name="Số Tài Khoản", value=f"```fix\n{account_no}```", inline=False)
            embed.add_field(name="Ngân Hàng", value=f"```fix\n{banking.name}```", inline=False)
            embed.add_field(name="Chủ Tài Khoản", value=f"```fix\n{namestk}```", inline=False)
            embed.add_field(name="Số Tiền", value=f"```fix\n{int(sotien)} đ```", inline=False)
            embed.add_field(name="Nội Dung", value=f"```fix\n{des}```", inline=False)
            embed.set_image(url=qr_url)

            if isinstance(interaction.channel, DMChannel):
                await interaction.user.send(embed=embed)
            else:
                await interaction.response.send_message(embed=embed)

            if save:
                self.log_command_to_db('banking', {
                    'user_id': interaction.user.id,
                    'user_name': interaction.user.name,
                    'guild_name': interaction.guild.name if interaction.guild else "DM",
                    'bank_name': banking.name,
                    'bank_id': banking.value,
                    'account_name': namestk,
                    'account_no': stk,
                    'amount': sotien,
                    'description': des,
                    'template': template,
                    'timestamp': datetime.now().isoformat(),
                    'command_text': command_text.lower() if command_text else None
                })
        else:
            await interaction.response.send_message("Đã xảy ra lỗi khi tạo QR code. Vui lòng thử lại sau.")
    @app_commands.command(name='qr_command',description="gửi qr qua lệnh có sẵn")
    @app_commands.user_install()
    @app_commands.guild_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True) 
    async def send_command(self,interaction:Interaction,command_text: str):
        command_text = command_text.lower()
        c.execute("SELECT * FROM banking WHERE command_text = ? ORDER BY timestamp DESC LIMIT 1", (command_text,))
        log = c.fetchone()

        if log:
            bank_id = log[5]
            account_no = log[7]
            template = log[10]
            amount = log[8]
            description = log[9].replace(" ", "%20")
            account_name = log[6].replace(" ", "%20")
            bank_name = log[4]

            qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-{template}.png?amount={amount}&addInfo={description}&accountName={account_name}"


            embed = Embed(
                title="QR Code",
                description="Chuyển Khoản Nhanh.",
                color=Color.random()
            )
            embed.add_field(name="Số Tài Khoản", value=f"```fix\n{account_no}```", inline=False)
            embed.add_field(name="Ngân Hàng", value=f"```fix\n{bank_name}```", inline=False)
            embed.add_field(name="Chủ Tài Khoản", value=f"```fix\n{account_name}```", inline=False)
            embed.add_field(name="Số Tiền", value=f"```fix\n{int(amount)} đ```", inline=False)
            embed.add_field(name="Nội Dung", value=f"```fix\n{description}```", inline=False)
            embed.set_image(url=qr_url)

            await interaction.response.send_message(embed=embed)
async def check_for_command_text(message: Message):
        if message.author == bot.user:
            return
        user_id = message.author.id
        command_text = message.content.lower()
        c.execute("SELECT command_text FROM banking WHERE user_id = ? AND LOWER(command_text) = ?", (user_id, command_text))
        result = c.fetchone()

        if result:
            command_text = result[0]
            c.execute("SELECT * FROM banking WHERE user_id = ? AND command_text = ? ORDER BY timestamp DESC LIMIT 1", (user_id, command_text))
            log = c.fetchone()

            if log:
                bank_id = log[5]
                account_no = log[7]
                template = log[10]
                sotien = log[8]
                description = log[9].replace(" ", "%20")
                account_name = log[6].replace(" ", "%20")
                bank_name = log[4]

                qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-{template}.png?amount={sotien}&addInfo={description}&accountName={account_name}"
                if qr_url.startswith("https://img.vietqr.io/image/"):
                    embed = Embed(
                        title="QR Code",
                        description="Chuyển Khoản Nhanh.",
                        color=Color.random()
                    )
                    bot_avatar_url = message.author.avatar.url if message.author.avatar else message.author.default_avatar.url
                    embed.set_author(name=message.author.display_name, icon_url=bot_avatar_url)
                    embed.set_thumbnail(url=bot_avatar_url)
                    embed.add_field(name="Số Tài Khoản", value=f"```fix\n{account_no}```", inline=False)
                    embed.add_field(name="Ngân Hàng", value=f"```fix\n{log[4]}```", inline=False)
                    embed.add_field(name="Chủ Tài Khoản", value=f"```fix\n{log[6]}```", inline=False)
                    embed.add_field(name="Số Tiền", value=f"```fix\n{int(sotien)} đ```", inline=False)
                    embed.add_field(name="Nội Dung", value=f"```fix\n{log[9]}```", inline=False)
                    embed.set_image(url=qr_url)
                    await message.channel.send(embed=embed)
@bot.event
async def on_ready():
  
    await bot.add_cog(BankingBot(bot))

    try:
        a= await bot.tree.sync()
        print(a)
    except Exception as e:
        print(f"Lỗi kết nối: {e}")
    
  
    print('Lệnh dồng bộ oke')
    
    activity = CustomActivity(name='Banking bot, hỗ trợ bán hàng nhanh nhất')
    await bot.change_presence(status=Status.online, activity=activity)

@bot.event
async def on_message(message: Message):
    await check_for_command_text(message)
    await bot.process_commands(message)

bot.run("")