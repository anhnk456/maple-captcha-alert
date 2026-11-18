# Maple CAPTCHA Alert

Cong cu chi chup mot vung man hinh, so khop voi cac template CAPTCHA hoac thong bao
duoc chon va phat tieng beep canh bao. Cong cu khong gui du lieu qua mang, khong doc bo nho game, khong tu
giai CAPTCHA va khong gui phim/chuot.

## Cai dat

Can Windows va Python 3.11 hoac 3.12 ban 64-bit. Khi cai Python, chon
**Add python.exe to PATH**.

```powershell
git clone https://github.com/anhnk456/maple-captcha-alert.git
cd maple-captcha-alert
.\start.cmd
```

Co the tai ZIP tu GitHub, giai nen roi nhay dup `start.cmd` thay cho lenh clone.
Lan dau, trinh khoi dong tu tao `.venv` va cai thu vien neu thieu; buoc cai thu
vien can Internet. Cac lan sau chi can nhay dup `start.cmd`.

Repo da bao gom du 10 anh mau trong `templates`, khong can chep them anh de chay.
Khong sao chep `.venv` giua cac may. Anh chup goc trong `samples` va anh canh bao
trong `detections` chi giu cuc bo vi co the chua thong tin nhan vat/chat;
chung khong can thiet cho viec giam sat.

Neu muon cai thu cong trong thu muc project:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Chuan bi template

1. Chup anh khi CAPTCHA xuat hien.
2. Dung Paint hoac Snipping Tool cat sat phan giao dien on dinh cua CAPTCHA.
3. Luu mot hoac nhieu anh PNG vao thu muc `templates`.
4. Luu anh co mau can canh bao vao `samples/captcha`, anh khong co mau vao `samples/normal`.

Bo template hien tai dung 10 mau duoc tao tu anh nguoi dung cung cap:

- `capcha1.png`: tieu de LIE DETECTOR cua hop thong bao mini-game.
- `capcha2.png`: dong chu Lie Detector nghieng, noi tren man hinh.
- `capcha4.png`: phan tren cua hinh cau vong, tranh dong chu thay doi.
- `capcha5.png`: dai huong dan mau xanh "Keep your eyes on the Violetta who's
  wearing make-up." trong mini-game chon nam; khong lay vi tri dap an hay nhan vat.
- `capcha6.png`: phan huong dan mau xanh trong hop Lie Detector ben phai,
  co dong "Please find the beautiful Violetta wearing make-up."; khong lay so dem
  nguoc, con tro chuot hay ten nhan vat.
- `lie-detector-title.png`: tieu de LIE DETECTOR co dinh trong anh game thuc te.
  Mau nay khong phu thuoc cau huong dan, day so hay vi tri nam trong mini-game;
  van can tieu de hien thi cung kich thuoc voi template.
- `lie-detector-shape.png`: phan huong dan co dinh "Move your mouse so that the
  cursor stays on the shape..." trong mini-game theo doi hinh. Khong lay so dem
  nguoc, hinh ngoi sao hay ten nhan vat. Mau duoc cat tu anh 608x470 va can cung
  kich thuoc giao dien de khop; khong tu phong to/thu nho.
- `lie-detector-activated.png`: hai dong chu vang "Lie Detector" va
  "has been activated." trong thong bao yeu cau bam chuot. Khong lay so dem
  nguoc, so lan bam chuot hay nhan vat; giu nguong khop mac dinh 0.8.
- `lie-detector-activated.yellow.png`: mat na hai dong chu tren, chi giu net
  chu trang tren nen den, khong giu nen game. Dung de nhan dien khi thong bao
  di chuyen sang nen khac, ke ca de len bang Quest Helper.
- `elite-boss-curse.png`: dong "Free the rune and lift the Elite Boss curse!".
  Day la thong bao Elite Boss Curse, khong phai CAPTCHA, duoc them de cung phat
  5 tieng beep theo yeu cau. Khong lay rieng bieu tuong o khoa hay dong phan tram
  vi chung co the xuat hien o noi khac hoac thay doi.

Ten template tuong ung voi anh goc cung ten trong `samples/captcha`.
Template khong lay ma CAPTCHA, so dem nguoc hay ten
nhan vat. Anh goc chi duoc dung lam du lieu kiem tra cuc bo va co the chua thong tin
nhan vat; khong chia se neu chua che thong tin rieng tu.

Template co duoi `.yellow.png` la mat na chu vang: net chu trang, nen den.
Khi kiem tra anh mau, cong cu tach chu vang bang HSV va lam mem nhe net chu
de giam anh huong rang cua/do nghieng nho, roi so khop voi mat na. Van dung
nguong chung 0.8 va can 2 khung hinh lien tiep trong che do giam sat.
Che do nay can anh mau BGR; anh xam chi duoc so voi cac template thong thuong.
Cac template khac van so khop anh xam nhu truoc.

Chu noi va hinh cau vong co nen trong suot, nen thay doi canh game, goc xoay hoac
kich thuoc co the lam giam diem khop. Can thu tren anh chup moi de danh gia kha nang
nhan dien; khop anh goc khong dam bao nhan dien moi lan CAPTCHA xuat hien.
Mat na chu vang cung khong dam bao khi chu bi che, mo dan hoac doi font/kich thuoc nhieu.
`samples/normal` chi chua anh that su khong co mau can canh bao.

Template va man hinh phai dung cung Windows display scale va do phan giai. Khong dua
ten nhan vat hoac thong tin tai khoan vao template.

## Kiem tra anh

```powershell
python main.py --threshold 0.8 check samples
```

Nguong khop mac dinh la 0.8, yeu cau diem khop cao hon de giam canh bao nham
nhung co the bo sot nhieu hon. Neu bo sot, giam threshold tung 0.05.
Neu bao nham, tang threshold tung 0.05.

## Giam sat va canh bao

Vi du giam sat vung 1280x720 bat dau tu goc trai man hinh:

```powershell
python main.py --threshold 0.8 monitor --region 0,0,1280,720
```

Chi chon vung cua so game de giam CPU va tranh chup thong tin rieng tu. Khi hai khung
hinh lien tiep khop template, cong cu beep va luu anh vao `detections`. Nhan `Ctrl+C`
de dung.

### Cach nhanh: nhay dup de chay

1. Mo game MapleStory va giu cua so hien thi.
2. Nhay dup [start.cmd](./start.cmd).
3. Cua so terminal co tieu de `Maple CAPTCHA Alert` hien thi trang thai truc tiep.
   Giu cua so nay mo va bat am thanh may tinh de nghe canh bao.

Sau khi cai thu vien, khong can cau hinh tai khoan hay Internet de giam sat.
Day la tu dong khi ban chay
chuong trinh, khong tu khoi dong cung Windows. Nhan `Ctrl+C` hoac dong cua so
terminal de dung. Chi mo mot ban chuong trinh de tranh canh bao trung lap.

Co the chay lenh tuong duong trong thu muc project:

```powershell
.\.venv\Scripts\python.exe main.py --threshold 0.8 monitor --window MapleStory
```

Cong cu tu tim cua so co tieu de dung `MapleStory`, `MapleStory N` hoac
`MapleStoryN` (khong phan biet hoa thuong), chup vung noi dung game va cap
nhat vi tri/kich thuoc khi cua so di chuyen. Chi theo doi khi cua so game dang
o phia truoc (dang duoc chon). Neu game dong, thu nho hoac ban chuyen sang VS Code/
ung dung khac, cong cu tam dung chup va in `[TAM DUNG]`. Chon lai cua so game
de tu tiep tuc va hien `[TIEP TUC]`. Cac thong bao nay kem thoi gian de doi chieu
khi kiem tra su co. Khong tu chup
toan man hinh khi khong tim thay game. Neu nhieu cua so trung ten, cong cu bao loi
va dung thay vi tu chon nham; dong cua so trung ten truoc khi chay lai.
Khong chon trang web chi co chu MapleStory trong tieu de. Neu ban game dung tieu de
khac, dung cach thu cong voi `--window "Tieu de chinh xac"` hoac `--region`.

Che do nay chup phan game dang hien thi tren desktop, khong chup ngam cua so bi che.
Cong cu kiem tra cua so truoc va sau khi chup, bo qua khung hinh neu game mat focus
hoac thay doi vi tri/kich thuoc trong luc chup. Giu game khong bi cua so khac che,
ke ca cua so luon o tren cung. Tuy chon `--region` van chup vung toa do co dinh,
khong kiem tra cua so hay focus.

Tu tim cua so khong khac phuc viec CAPTCHA
thay doi kich thuoc, display scale, goc xoay hoac nen. Hai tuy chon `--window` va
`--region` khong duoc dung cung luc.

Mac dinh chup moi 0.75 giay (`--interval`), can 2 khung hinh lien tiep
(`--confirm-frames`) va cho it nhat 30 giay giua cac lan canh bao (`--cooldown`).
Moi lan canh bao phat 5 tieng beep va luu anh bang chung tren may trong
`detections`. Anh co the chua thong tin nhan vat; khong chia se khi chua che
thong tin rieng tu.

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Cac kiem thu can anh chup goc se hien `skipped` neu clone moi chua co anh cuc bo
trong `samples`; cac kiem thu logic van chay. Chep bo anh goc vao dung thu muc
neu muon chay day du kiem thu anh. Khong dua anh chua che thong tin rieng tu len GitHub.

Hay kiem tra dieu khoan cua may chu MapleStory ban dang choi. Khong mo rong cong cu
thanh chuc nang tu giai, tu thao tac hoac ne he thong chong gian lan.
