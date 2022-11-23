from pathlib import Path
from TGConvertor.manager.manager import SessionManager


def main():
    session = SessionManager.from_tdata_folder(Path("TDATA/tdata"))
    res = session.to_pyrogram_string()
    print(res)


if __name__ == "__main__":
    main()
