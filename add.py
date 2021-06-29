import asyncio
import os
import sys
from typing import Union, List
import pyrogram
from pyrogram import Client, raw, filters
from pyrogram.handlers import MessageHandler
from pyrogram.errors import RPCError, UserAlreadyParticipant, PeerIdInvalid, FloodWait

re="\033[1;31m"
gr="\033[1;32m"
cy="\033[1;36m"

def bannel():
    os.system('clear')
    print(f"""
{re}TOOL THÊM THÀNH VIÊN VÀO NHÓM TELEGRAM
{cy}Tác giả: Kuri - t.me/cunongdan
       """)


CLIENTS_DIR = './clients'
MAX_ADD_COUNT = 50
SLEEP_INTERVALS = 1
RETRIES = 2
ORIGIN_CHAT = ''
DESTINATION_CHAT = 'baongu69'

pyrogram.session.Session.notice_displayed = True


_used_ids = set()


class FakeClient(Client):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.participants_q = asyncio.Queue()
        self.add_task = None
        self.extract_task = None

    async def extract_members(self, chat_id: int):
        async for member in self.iter_chat_members(chat_id):
            try:
                user = member.user
                if not (user.is_self or user.is_deleted):
                    member_peer = await self.resolve_peer(user.id)
                    await self.participants_q.put(
                        raw.types.InputUser(user_id=member_peer.user_id, access_hash=member_peer.access_hash)
                    )
            except Exception as e:
                print(f"""{cy}    - Tài khoản {self.session_name} Exp : {e}""")
        await self.participants_q.put(None)

    async def add_progress(self, chat_id, once=True):
        global _used_ids
        adding = True
        user_peers = []
        while adding:

            while len(user_peers) < MAX_ADD_COUNT:
                user_peer = await self.participants_q.get()
                if user_peer is None:
                    adding = False
                    break
                if user_peer.user_id in _used_ids:
                    continue
                else:
                    _used_ids.add(user_peer.user_id)
                user_peers.append(user_peer)

            if user_peers:
                for _ in range(2):
                    try:
                        amount = await self.add_chat_members(chat_id, user_peers)
                        print(f'      - Tài khoản {self.session_name}: Thêm {amount}/{len(user_peers)} thành viên')
                    except FloodWait as e:
                        await asyncio.sleep(e.x + 1)
                        continue
                    except RPCError as e:
                        print(f'        - Tài khoản {self.session_name} Ngoại lệ: {e}')
                    break
            if once:
                adding = False
            else:
                await asyncio.sleep(1)

        if self.extract_task is not None:
            self.extract_task.cancel()

    async def get_chat_id(self, chat_id):
        try:
            chat_id = int(chat_id)
        except ValueError:
            try:
                return (await self.join_chat(chat_id)).id
            except UserAlreadyParticipant:
                pass

        return (await self.get_chat(chat_id)).id

    async def add_chat_members(
            self,
            chat_id: Union[int, str],
            user_ids: Union[Union[int, str, 'raw.types.InputUser'], List[Union[int, str, 'raw.types.InputUser']]],
            forward_limit: int = 100
    ) -> int:

        if isinstance(user_ids, raw.types.InputUser):
            user_peers = [user_ids]
        elif isinstance(user_ids, list) and all([isinstance(user_id, raw.types.InputUser) for user_id in user_ids]):
            user_peers = user_ids
        else:
            return await super().add_chat_members(chat_id, user_ids, forward_limit)

        peer = await self.resolve_peer(chat_id)
        amount = 0
        if isinstance(peer, raw.types.InputPeerChat):
            for user_peer in user_peers:
                await self.send(
                    raw.functions.messages.AddChatUser(
                        chat_id=peer.chat_id,
                        user_id=user_peer,
                        fwd_limit=forward_limit
                    )
                )
                amount += 1
        else:
            res = await self.send(
                raw.functions.channels.InviteToChannel(
                    channel=peer,
                    users=user_peers
                )
            )
            amount += len(res.users)
        return amount


async def main(once=True):
    ori_text = gr+'ID/Username nhóm cào member: '
    des_text = gr+'ID/Username nhóm tăng member: '
    if ORIGIN_CHAT:
        origin_chat = ORIGIN_CHAT
        print(f'{cy}- {ori_text} {ORIGIN_CHAT}')
    else:
        origin_chat = input(f"""{gr}- Nhập {ori_text}""")

    if DESTINATION_CHAT:
        destination_chat = DESTINATION_CHAT
        print(f'- {des_text} {DESTINATION_CHAT}')
    else:
        destination_chat = input(f"""{gr}- Nhập {des_text}""")

    print("""{cy} - Bắt đầu khởi động: """)

    # session_names = map(lambda f: f.replace('.session', ''),
    # filter(lambda f: f.endswith(".session"), os.listdir(CLIENTS_DIR)))
    # for session_name in session_names:

    clients = []

    for f in os.listdir('./clients'):
        if not f.endswith(".session"):
            continue
        session_name = f.replace('.session', '')
        print(f'{cy}\n- Tài khoản {session_name}')
        client = FakeClient(session_name, workdir='./clients')
        await client.start()
        print(f'{cy}  - Tài khoản {session_name} - Bắt đầu')
        clients.append(client)

        # Ensure we got origin chat
        print(f"""{cy}  - Tài khoản {session_name}: Xác định nhóm cào member""")
        try:
            origin_chat_id = await client.get_chat_id(origin_chat)
        except (KeyError, ValueError, PeerIdInvalid):
            print(f"""{cy}  - Tài khoản {session_name} - Ngoại lệ: Không tìm thấy nhóm cào member""")
            continue
        except RPCError as e:
            print(f"""{cy}  - Tài khoản {session_name} - Ngoại lệ: {e}""")
            continue
        print(f"""{cy}  - Tài khoản {session_name}: ID nhóm cạo: {origin_chat_id}""")

        client.extract_task = asyncio.ensure_future(client.extract_members(origin_chat_id))

        # Ensure we got destination chat
        print(f"""{cy}  - Tài khoản {session_name}: Xác định nhóm add member""")
        try:
            target_chat_id = await client.get_chat_id(destination_chat)
        except (KeyError, PeerIdInvalid):
            print(f"""{cy}  - Tài khoản {session_name} - Ngoại lệ: Không tìm thấy nhóm add member""")
            continue
        except RPCError as e:
            print(f"""{cy}  - Tài khoản {session_name} - Ngoại lệ: {e.x}""")
            continue
        print(f"""{cy}  - Client({session_name}): ID nhóm tăng: {target_chat_id}""")

        print(f"""{cy}    - Client({session_name}): Ò e ò e...""")

        client.add_task = asyncio.ensure_future(client.add_progress(target_chat_id, once=once))

    await asyncio.gather(*[clt.add_task for clt in clients if clt.add_task is not None], return_exceptions=True)
    await asyncio.gather(*[clt.stop() for clt in clients])


async def report_status():
    clients = []
    for f in os.listdir('./clients'):
        if not f.endswith(".session"):
            continue
        session_name = f.replace('.session', '')
        print(f"""{cy} \n    - Kiểm tra tài khoản {session_name}""")
        client = Client(session_name, workdir='./clients')
        clients.append(client)
        await clients[-1].start()
        clients[-1].add_handler(MessageHandler(callback=lambda c, m: print(m.text), filters=filters.user('SpamBot')))
    for client in clients:
        await client.send(
            raw.functions.messages.StartBot(
                bot=await client.resolve_peer('SpamBot'),
                peer=await client.resolve_peer('SpamBot'),
                random_id=client.rnd_id(),
                start_param='start'
            )
        )

    for client in clients:
        await client.stop()


async def add_client():
    session_name = input(gr+'Nhập tên phiên: ')
    async with Client(session_name, workdir='./clients') as new_client:
        print(f'{cy}- Tài khoản mới {new_client.storage.database}')


if __name__ == "__main__":

    if not os.path.exists(CLIENTS_DIR):
        os.mkdir(CLIENTS_DIR)

    if len(sys.argv) == 1:
        bannel()
        func = main()
    elif len(sys.argv) == 2:
        if sys.argv[1] == '--add':
            bannel()
            func = add_client()
        elif sys.argv[1] == '--check':
            bannel()
            func = report_status()
        elif sys.argv[1] == '--continue':
            bannel()
            func = main(once=False)
        else:
            exit('BAD ARGS')
    else:
        exit('BAD ARGS')
        

    print('\nBắt đầy tại đây...\n')

    loop = asyncio.get_event_loop()
    loop.run_until_complete(func)
    loop.close()

    print('\nHoàn thành!\n')
