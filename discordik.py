import discord
from discord.ext import commands

import sqlite3
from config import settings

bot = commands.Bot(command_prefix=settings['PREFIX'], intents=discord.Intents.all())
bot.remove_command('help')

connection = sqlite3.connect('usertable.db')
cursor = connection.cursor()


@bot.event
async def on_ready():
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        name TEXT,
        id INT,
        cash INT,
        rep INT,
        lvl INT,
        server_id INT
    )""")
    connection.commit()

    cursor.execute("""CREATE TABLE IF NOT EXISTS shop (
            role_id INT,
            id INT,
            cost INT
        )""")

    for guild in bot.guilds:
        for member in guild.members:
            if cursor.execute(f"SELECT id FROM users WHERE id = {member.id}").fetchone() is None:
                cursor.execute(f"INSERT INTO users VALUES ('{member}', {member.id}, 0, 0, 1, {guild.id})")
                connection.commit()
            else:
                pass

    connection.commit()
    print('Бот подключён')


@bot.event
async def on_member_join(member):
    if cursor.execute(f"SELECT id FROM users WHERE id = {member.id}").fetchone() is None:
        cursor.execute(f"INSERT INTO users VALUES ('{member}', {member.id}, 0, 0, 1, {member.guild.id})")
        connection.commit()
    else:
        pass


@bot.command(aliases=['cash'])
async def balance(par, member: discord.Member = None):
    if member is None:
        await par.send(embed=discord.Embed(
            description=f"""Баланс пользователя **{par.author}** составляет **{cursor.execute("SELECT cash FROM users WHERE id = {}".format(par.author.id)).fetchone()[0]} :dollar:**"""
        ))

    else:
        await par.send(embed=discord.Embed(
            description=f"""Баланс пользователя **{member}** составляет **{cursor.execute("SELECT cash FROM users WHERE id = {}".format(member.id)).fetchone()[0]} :dollar:**"""
        ))


@bot.command(aliases=['accrue', 'award'])
async def deposit(par, member: discord.Member = None, amount: int = None):
    if member is None:
        await par.send(f"**{par.author}**, укажите пользователя, которому хотите выдать определенную сумму")
    else:
        if amount is None:
            await par.send(f"**{par.author}**, укажите сумму, которую хотите начислить на счет пользователя")
        elif amount < 1:
            await par.send(f"**{par.author}**, укажите сумму больше 1 :dollar:")
        else:
            cursor.execute("UPDATE users SET cash = cash + {} WHERE id = {}".format(amount, member.id))
            connection.commit()

            await par.message.add_reaction('👍🏼')


@bot.command(aliases=['забрать', 'обчистить'])
async def take(par, member: discord.Member = None, amount=None):
    if member is None:
        await par.send(f"**{par.author}**, укажите пользователя, у которого хотите отнять сумму денег")
    else:
        if amount is None:
            await par.send(f"**{par.author}**, укажите сумму, которую хотите отнять у счета пользователя")
        elif amount == 'all':
            cursor.execute("UPDATE users SET cash = {} WHERE id = {}".format(0, member.id))
            connection.commit()

            await par.message.add_reaction('👍🏼')
        elif int(amount) < 1:
            await par.send(f"**{par.author}**, укажите сумму больше 1 :dollar:")
        else:
            cursor.execute("UPDATE users SET cash = cash - {} WHERE id = {}".format(int(amount), member.id))
            connection.commit()

            await par.message.add_reaction('👍🏼')


@bot.command(aliases=['add-shop'])
async def add_shop(par, role: discord.Role = None, cost: int = None):
    if role is None:
        await par.send(f"**{par.author}**, укажите роль, которую вы хотите внести в магазин")
    else:
        if cost is None:
            await par.send(f"**{par.author}**, укажите стоимость для данной роли")
        elif cost < 0:
            await par.send(f"**{par.author}**, стоимость роли не может быть такой маленькой")
        else:
            cursor.execute("INSERT INTO shop VALUES ({}, {}, {})".format(role.id, par.guild.id, cost))
            connection.commit()

            await par.message.add_reaction('👍🏼')


@bot.command(aliases=['remove-shop'])
async def remove_shop(par, role: discord.Role = None):
    if role is None:
        await par.send(f"**{par.author}**, укажите роль, которую вы хотите удалить из магазина")
    else:
        cursor.execute("DELETE FROM shop WHERE role_id = {}".format(role.id))
        connection.commit()

        await par.message.add_reaction('👍🏼')


@bot.command(aliases=['магазин'])
async def shop(par):
    embed = discord.Embed(title='Магазин ролей')

    for row in cursor.execute("SELECT role_id, cost FROM shop WHERE id = {}".format(par.guild.id)):
        if par.guild.get_role(row[0]) != None:
            embed.add_field(
                name=f"Стоимость {row[1]} :dollar:",
                value=f"Роль {par.guild.get_role(row[0]).mention}",
                inline=False
            )
        else:
            pass

    await par.send(embed=embed)


@bot.command(aliases=['купить', 'buy-role'])
async def buy(par, role: discord.Role = None):
    if role is None:
        await par.send(f"**{par.author}**, укажите роль, которую вы хотите приобрести")
    else:
        if role in par.author.roles:
            await par.send(f"**{par.author}**, у вас уже есть данная роль")
        elif cursor.execute("SELECT cost FROM shop WHERE role_id = {}".format(role.id)).fetchone()[0] > \
                cursor.execute("SELECT cash FROM users WHERE id = {}".format(par.author.id)).fetchone()[0]:
            await par.send(f"**{par.author}**, у вас недостаточно средств для покупки данной роли")
        else:
            await par.author.add_roles(role)
            cursor.execute("UPDATE users SET cash = cash - {} WHERE id = {}".format(
                cursor.execute("SELECT cost FROM shop WHERE role_id = {}".format(role.id)).fetchone()[0],
                par.author.id))
            connection.commit()
            cursor.execute("UPDATE users SET lvl = lvl + 1 WHERE id = {}".format(par.author.id))

            await par.send(f'Поздравляем, Вы приобрели Роль {role}. Ваш уровень повышен!')
            await par.message.add_reaction('👍🏼')


@bot.command(aliases=['reputation', '+rep', 'репутация'])
async def rep(par, member: discord.Member = None):
    if member is None:
        await par.send(f"**{par.author}**, укажите участника сервера")
    else:
        if member.id == par.author.id:
            await par.send(f"**{par.author}**, вы не можете указать самого себя")
        else:
            cursor.execute("UPDATE users SET rep = rep + {} WHERE id = {}".format(1, member.id))
            connection.commit()

            await par.message.add_reaction('👍🏼')


@bot.command(aliases=['level'])
async def lvl(par, member: discord.Member = None):
    if member is None:
        await par.send(embed=discord.Embed(
            description=f"""Уровень пользователя **{par.author}** составляет **{cursor.execute("SELECT lvl FROM users WHERE id = {}".format(par.author.id)).fetchone()[0]} :zap:**"""
        ))

    else:
        await par.send(embed=discord.Embed(
            description=f"""Уровень пользователя **{member}** составляет **{cursor.execute("SELECT lvl FROM users WHERE id = {}".format(member.id)).fetchone()[0]} :zap:**"""
        ))


@bot.command(aliases=['богачи', 'lb_money'])
async def leaderboard_money(par):
    embed = discord.Embed(title='Топ 10 богатейших людей сервера')
    counter = 0

    for row in cursor.execute(
            "SELECT name, cash FROM users WHERE server_id = {} ORDER BY cash DESC LIMIT 10".format(par.guild.id)):
        counter += 1
        embed.add_field(
            name=f'№ {counter} | `{row[0]}`',
            value=f'Баланс: {row[1]}',
            inline=False
        )

    await par.send(embed=embed)


@bot.command(aliases=['уважаемые', 'lb_rep'])
async def leaderboard_rep(par):
    embed = discord.Embed(title='Топ 10 уважаемых людей сервера')
    counter = 0

    for row in cursor.execute(
            "SELECT name, rep FROM users WHERE server_id = {} ORDER BY rep DESC LIMIT 10".format(par.guild.id)):
        counter += 1
        embed.add_field(
            name=f'# {counter} | `{row[0]}`',
            value=f'Репутация: {row[1]}',
            inline=False
        )

    await par.send(embed=embed)


@bot.command(aliases=['опытные', 'lb_lvl'])
async def leaderboard_lvl(par):
    embed = discord.Embed(title='Топ 10 опытных людей сервера')
    counter = 0

    for row in cursor.execute(
            "SELECT name, lvl FROM users WHERE server_id = {} ORDER BY lvl DESC LIMIT 10".format(par.guild.id)):
        counter += 1
        embed.add_field(
            name=f'# {counter} | `{row[0]}`',
            value=f'Уровень: {row[1]}',
            inline=False
        )

    await par.send(embed=embed)


bot.run(settings['TOKEN'])
