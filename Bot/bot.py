import logging
import pickle
import socket
from threading import Thread

from apscheduler.schedulers.background import BackgroundScheduler
from time import sleep

from GameList import GameList
from account_creator import create_account
from dotenv import load_dotenv
from os import getenv
from Networking.packet_types import ServerRegisterAnswer, TimeTable, DynamicTimeSchedule, \
    LoginTimeSchedule, GamesListSchedule, AccountRegisterRequest, BotRegisterRequest, GameDetail
from game import Game
import logger

load_dotenv()


class Bot:
    def __init__(self):

        logger.initLogger(5)
        self.registered = False
        self.server_uuid = getenv("SERVER_UUID")
        self.client = socket.socket()
        self.connected = False

        self.login_scan_queue = []
        self.working_on_login_scan_queue = False
        self.scheduler = BackgroundScheduler()
        self.scheduler.remove_all_jobs()
        self.games_list = None
        self.games = []
        self.game_table = None
        self.time_table = None

    def run(self):
        self.scheduler.start()
        self.client = socket.socket()
        self.connect_to_server((getenv("COMMUNICATION_IP"), int(getenv("COMMUNICATION_PORT"))))
        if self.connected:
            self.register_server()
            self.main_loop()

    def connect_to_server(self, server_addr):
        for i in range(int(getenv("RECONNECT_TRIES"))):
            try:
                self.client.connect(server_addr)
                self.connected = True
                logging.debug(f"Connected to Manager {server_addr[0]}")
                break
            except socket.error:
                sleep(2)
        else:
            logging.debug(f"Connecting to Manager {server_addr[0]} failed")

    def send_packet(self, packet):
        packet_encoded = pickle.dumps(packet)
        buffer_length = len(packet_encoded)

        buffer_enc_length = str(buffer_length).encode(getenv("FORMAT"))
        buffer_enc_length += b' ' * (
                int(getenv("HEADER")) - len(buffer_enc_length))  # fill up buffer, until it has the expected size

        self.client.send(buffer_enc_length)
        self.client.send(packet_encoded)

    def register_server(self):
        packet = BotRegisterRequest(server_uuid=getenv("SERVER_UUID"),
                                    maximum_games=int(getenv("MAXIMUM_GAMES")))
        self.send_packet(packet)

    def main_loop(self):
        while True:
            try:
                buffer_size = self.client.recv(int(getenv("HEADER"))).decode(getenv("FORMAT"))
                if not buffer_size:
                    break
            except OSError:
                break

            data = self.client.recv(int(buffer_size))
            if not data:
                break

            packet = pickle.loads(data)
            answer_thread = None
            if isinstance(packet, ServerRegisterAnswer):
                answer_thread = Thread(target=self.handle_register_server_answer, args=(packet,))
            elif isinstance(packet, AccountRegisterRequest):
                answer_thread = Thread(target=self.handle_register_account_request, args=(packet,))
            elif isinstance(packet, TimeTable):
                self.time_table_thread = Thread(target=self.handle_time_table, args=(packet,))
                self.time_table_thread.start()

            if answer_thread:
                answer_thread.start()

    def work_login_scan_queue(self):
        print(self.login_scan_queue)
        if not self.working_on_login_scan_queue:
            self.working_on_login_scan_queue = True
            while len(self.login_scan_queue) > 0:
                print(self.login_scan_queue)

                game = self.get_game("game_id", self.login_scan_queue[0])
                try:
                    game.long_game_scan()
                except Exception as exception:
                    print(exception)

                try:
                    self.login_scan_queue.remove(game.game_id)
                except ValueError:
                    logging.debug(f"G: {game.game_id} couldn't remove game from login scan queue")
        self.working_on_login_scan_queue = False

    def handle_register_server_answer(self, packet: ServerRegisterAnswer):
        if packet.successful:
            logging.debug("Registered successful")
        else:
            raise packet.response_code

    def handle_register_account_request(self, packet: AccountRegisterRequest):
        answer = create_account(packet)
        self.send_packet(answer)

    def handle_time_table(self, packet: TimeTable):
        self.time_table = packet

        # Add all necessary Games
        for schedule in self.time_table.schedules:
            game_detail = GameDetail(
                game_id=schedule.game_id,
                account_id=schedule.account_id,
                server_uuid=schedule.server_uuid,
                email=schedule.email,
                username=schedule.username,
                password=schedule.password,
                local_ip=schedule.local_ip,
                local_port=schedule.local_port,
                joined=schedule.joined,
                proxy_username=schedule.proxy_username,
                proxy_password=schedule.proxy_password,
            )
            if not any([schedule.game_id == game.game_id for game in self.games]):
                self.games.append(Game(game_detail))
            else:
                for game in self.games:
                    if game.game_id == schedule.game_id:
                        game.game_detail = game_detail
                        break

        self.scheduler.remove_all_jobs()
        for schedule in self.time_table.schedules:
            if isinstance(schedule, GamesListSchedule):
                needs_run = not isinstance(self.games_list, GameList)
                self.games_list = GameList(schedule)
                self.scheduler.add_job(self.games_list.game_list_run, "interval",
                                       start_date=schedule.start_date,
                                       seconds=schedule.interval,
                                       name=f"GLS -> A: {schedule.game_id}")

                if needs_run:
                    game_list_thread = Thread(target=self.games_list.game_list_run)
                    game_list_thread.start()
            else:
                schedule: DynamicTimeSchedule | LoginTimeSchedule
                game = self.get_game("game_id", schedule.game_id)
                if isinstance(schedule, DynamicTimeSchedule):
                    dynamic_job = self.scheduler.add_job(game.short_game_scan, "interval",
                                                         start_date=schedule.start_date,
                                                         seconds=schedule.interval,
                                                         name=f"DS -> G: {game.game_id} A: {game.game_detail.account_id}")
                    game.dynamic_job = dynamic_job
                elif isinstance(schedule, LoginTimeSchedule):
                    login_job = self.scheduler.add_job(game.long_game_scan, "interval",
                                                       start_date=schedule.start_date,
                                                       seconds=schedule.interval,
                                                       name=f"LS -> G: {game.game_id} A: {game.game_detail.account_id}")
                    game.login_job = login_job
                    if not game.auth_data and game.game_id not in self.login_scan_queue:
                        self.add_game_to_login_scan_queue(game.game_id, urgent=not game.game_detail.joined)

        self.work_login_scan_queue()

    def add_game_to_login_scan_queue(self, game_id, urgent=False):
        if urgent:
            self.login_scan_queue.insert(0, game_id)
        else:
            self.login_scan_queue.append(game_id)

    def get_game(self, key, data):
        for game in self.games:
            if getattr(game, key) == data:
                return game


if __name__ == "__main__":
    bot = Bot()
    bot.run()
