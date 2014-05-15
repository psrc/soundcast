program DaySimParcelBufferingV3;

{$MODE Delphi}

{$APPTYPE CONSOLE}

uses
  SysUtils;

const
(* ======== USER CONTROL CONSTANTS ========= *)

runlabel:string           = 'Parcel buffering run';

(* file names and paths *)
outdir:string             ='..\'; {output file directory}
inputdir:string           ='..\'; {input file directory}

{on all input file names except parcel file, use string 'none' if no file is available}

printfname:string         ='parcel_buffering.prn';
outfname:string           ='parcel_buffered.dat';  {output file name }
outfdelim:integer         = 1;                        {output file delimeter 1=space 2=tab 3=comma}
parcelfname:string        ='parcelbase.dat';          {parcel data file name }
intsecfname:string        ='intersections.dat';       {intersection data file name }
trnstpfname:string        ='transitstops.dat';        {transit stop data file name }
opnspcfname:string        ='openspace.dat';           {open space data file name }
circuityfname:string      ='NONE';                    {parcel circuity data file name}
nodefname:string          ='node_xys.dat';            {node data file name }
nodenodedistancefname:string ='NONE';                 {node-node distance binary file name}

nodeftype:integer         = 2;                        {parcel file type 1=dbf, 2=ascii}
parcelftype:integer       = 1;                        {parcel file type 1=dbf, 2=ascii}
intsecftype:integer       = 1;                        {intersection file type 0=none 1=dbf, 2=ascii}
trnstpftype:integer       = 1;                        {transit stop file type 0=none 1=dbf, 2=ascii}
opnspcftype:integer       = 1;                        {open space file type   0=none 1=dbf, 2=ascii}
circuityftype:integer     = 0;                        {circuity file type   0=none 1=dbf, 2=ascii  3 node-to-node files}
circuityfdiff:integer     = 0;

(* buffer parameters *)
bufftype1:integer = 1;
buffdist1:single =  1320.0; {buffer 1 distance in feet - for flat, this is limit, for decay, this is inflection point}
buffdecay1:single = 0.9;    {buffer 1 decay slope - use 0 for flat buffers, 0.9 for decay buffers}
buffexpon1:single = -2.5205; {buffer 1 exponential decay parameter - not currently used}
buffoffset1:single = 0.25;
bufftype2:integer = 1;
buffdist2:single = 2640.0; {buffer 2 distance in feet - for flat, this is limit, for decay, this is inflection point}
buffdecay2:single = 0.9;     {buffer 2 decay slope - use 0 for flat buffers, 0.9 for decay buffers}
buffexpon2:single = -0.4365; {buffer 2 exponential decay parameter}
buffoffset2:single = 0.35;

buffdlimit:single = 15840.0; {orthogonal distance to be considered for either buffer (for processing speed)}

prtfileopen:integer       = 0;
waittoexit:integer       = 1;

frstpercent:integer =0;
lastpercent:integer =100;


var prtf:text; timestring:string;
dlm:string[1];

procedure pwriteln(pri:integer; s:string);
begin
    writeln(s);
    if prtfileopen>0 then begin
      writeln(prtf,s); flush(prtf);
    end;
end;

procedure pwrite(pri:integer; s:string);
begin
    write(s);
    if prtfileopen>0 then begin
      write(prtf,s); flush(prtf);
    end;
 end;


function openTextFile(var f:text; fn:string; rorw:integer):integer;
var i:integer;
begin
  {$I-} assign(f,fn); if rorw<>2 then reset(f) else rewrite(f); {$I+}
  i:=IOResult;
  if i>0 then pwriteln(1,'Cannot open text file '+fn) else
  if rorw<>2 then pwriteln(1,'Opened text file '+fn+' for input') else
                  pwriteln(1,'Opened text file '+fn+' for output');
  opentextfile:=i;
end;

procedure openPrintFile;
begin
  assign(prtf,printfname); rewrite(prtf);
  prtfileopen:=1;
end;

procedure GetRunControls;
var
inf:text;
ctlfname,cstr:string;


procedure processCstr(cstr:string);
var p,cerr:integer; clab,carg:string;
begin
   for p:=1 to length(cstr) do if cstr[p]='=' then cstr[p]:=' ';

   cerr:=0;
   p:=1;
   while (cstr[p]=' ') and (p<length(cstr)) do p:=p+1;

   if p<length(cstr) then begin

     clab:='';
     repeat
       clab:=clab+uppercase(cstr[p]);
       p:=p+1;
     until (cstr[p]=' ') or (p>=length(cstr));
     clab:=copy(clab,1,6);

     if p<length(cstr) then begin

       while (cstr[p]=' ') and (p<length(cstr)) do p:=p+1;

       if p<=length(cstr) then begin

         carg:='';
         repeat
           carg:=carg+cstr[p];
           p:=p+1;
         until (p>length(cstr)) or ((cstr[p]=' ') and (clab<>'RUNLAB'));

         if clab='RUNLAB' then runlabel:=carg else
         if clab='PRNTFN' then begin printfname:=carg; openPrintFile; end else

         if clab='OUTDIR' then outdir:=carg else
         if clab='OUTFNM' then outfname:=carg else
         if clab='OUTDLM' then outfdelim:=strtoint(carg) else
         if clab='INPDIR' then inputdir:=carg else
         if clab='PARCFN' then parcelfname:=carg else
         if clab='INTSFN' then intsecfname:=carg else
         if clab='TRSTFN' then trnstpfname:=carg else
         if clab='OPSPFN' then opnspcfname:=carg else
         if clab='NODEFN' then nodefname:=carg else
         if clab='CIRCFN' then circuityfname:=carg else
         if clab='NDSTFN' then nodenodedistancefname:=carg else
         if clab='PARCFT' then parcelftype:=strtoint(carg) else
         if clab='INTSFT' then intsecftype:=strtoint(carg) else
         if clab='TRSTFT' then trnstpftype:=strtoint(carg) else
         if clab='OPSPFT' then opnspcftype:=strtoint(carg) else
         if clab='NODEFT' then nodeftype:=strtoint(carg) else
         if clab='CIRCFT' then circuityftype:=strtoint(carg) else
         if clab='CIRCDF' then circuityfdiff:=strtoint(carg) else

         if clab='DLIMIT' then buffdlimit:=strtofloat(carg) else

         if clab='BTYPE1' then bufftype1:=strtoint(carg) else
         if clab='BDIST1' then buffdist1:=strtofloat(carg) else
         if clab='DECAY1' then buffdecay1:=strtofloat(carg) else
         if clab='BOFFS1' then buffoffset1:=strtofloat(carg) else
         if clab='EXPON1' then buffexpon1:=strtofloat(carg) else

         if clab='BTYPE2' then bufftype2:=strtoint(carg) else
         if clab='BDIST2' then buffdist2:=strtofloat(carg) else
         if clab='DECAY2' then buffdecay2:=strtofloat(carg) else
         if clab='BOFFS2' then buffoffset2:=strtofloat(carg) else
         if clab='EXPON2' then buffexpon2:=strtofloat(carg) else

         if clab='FRSTPC' then frstpercent:=strtoint(carg) else
         if clab='LASTPC' then lastpercent:=strtoint(carg) else


         cerr:=1;

       end else cerr:=1;
     end else cerr:=1;
   end else cerr:=1;

   if cerr>0 then begin
      write('Unknown control line : ',cstr,'    <Press Enter to continute>'); readln;
   end;


end;

var i:integer;
begin
  if (ParamCount>0)  then ctlfname:=ParamStr(1) else
  begin
    writeln;
    ctlfname:='psrc2006 - decay and node.ctl';
    { write('Give name of control input file and press Enter : ');  readln(ctlfname);}
  end;

  if ctlfname<>'' then begin
    if openTextFile(inf,ctlfname,1)=0 then begin
      repeat
         readln(inf,cstr);
         if (cstr<>'') and (ord(cstr[1])<>26) then processCstr(cstr);
      until eof(inf);
      close(inf);
    end;
  end;

  if prtfileopen<1 then openPrintFile;

  {process rest of command line parameters}
  for i:=2 to ParamCount do processCstr(ParamStr(i));

  {start print file, and write controls to it }

  pwriteln(1,runlabel);
  pwriteln(1,'');
  timestring:=DateTimetoStr(now);
  pwriteln(1,'Run for control file '+ctlfname+' started at  '+timestring);
  pwriteln(1,'');
  if ctlfname<>'NONE' then begin
     pwriteln(1,'Control file contents: ');
     if openTextFile(inf,ctlfname,1)=0 then begin
       repeat
         readln(inf,cstr);

         pwriteln(1,cstr);
       until eof(inf);
       close(inf);
     end;
  end;
  if paramcount>1 then begin
     pwriteln(1,'Command line switches: ');
     for i:=2 to paramcount do pwriteln(1,paramstr(i));
  end;
end;




{//////////////// routines to read and write dBase IV files ////////////}

{Data types}
const maxfld=256; maxrecln=4000;
type
    dbfftype=file;
    dbfhrecord=record
      nrecs, nflds, recln, filestat,hhsrat,hhsbeg:integer;  {number of records, fields, record length, file status:0complete 1+partial,hh sampling rate, hh beginning number}
      fname:array[1..maxfld] of string[11]; {field names}
      ftyp:array[1..maxfld] of byte; {field types}
      flen:array[1..maxfld] of byte; {field lengths}
      fdec:array[1..maxfld] of byte; {field decimals}
      fdisp:array[1..maxfld] of integer; {field displacement in a record}
      currec:array[1..maxrecln] of char;
    end;

function openDBFFile(var f:dbfftype; fn:string; rorw:integer):integer;
var i:integer;
begin
  {$I-} assign(f,fn); if rorw<>2 then reset(f,1) else rewrite(f,1); {$I+}
  i:=IOResult;
  if i>0 then pwriteln(1,'Cannot open DBase file : '+fn) else
  if rorw<>2 then pwriteln(1,'Opened DBase file '+fn+' for input') else
                  pwriteln(1,'Opened DBase file '+fn+' for output');
  openDBFfile:=i;
end;

{//// Procedure to read header record information}
procedure readDBFFileHeader( var dbfil:dbfftype; var dbhrec:dbfhrecord);
var
b:byte; i,j,posfr,nread:integer; hb:array[0..31] of byte;

begin
 with dbhrec do begin
{reset to beginning of file}
  seek(dbfil,0);
{read in first 32 bytes of files}
  blockread(dbfil,hb,sizeof(hb),nread);
  pwriteln(1,'dBase file last updated: '+inttostr(hb[3])+'/'+inttostr(hb[2])+'/'+inttostr(hb[1]));
{parse out number of records and fields, and record length, in bytes}
  nrecs:=round(hb[4]+256.0*hb[5]+256*256.0*hb[6]+256*256*256.0*hb[7]);
  posfr:=hb[8]+256*hb[9];
  nflds:=(posfr-33) div 32;
  recln:=hb[10]+256*hb[11];
  {parse files status, hh sampling rate and hh beginning parms}
  filestat:=hb[12];
  hhsrat:=round(hb[13]+256.0*hb[14]+256*256.0*hb[15]+256*256*256.0*hb[16]);
  hhsbeg:=round(hb[17]+256.0*hb[18]+256*256.0*hb[19]+256*256*256.0*hb[20]);
  pwriteln(1,'File has '+inttostr(nflds)+' data fields  and '+inttostr(nrecs)+' records of '+inttostr(recln)+' bytes');

{parse out field names, types, lengths, and decimals, and calculate displacements}
  posfr:=1;
  for i:=1 to nflds do begin
    fname[i]:='';
    blockread(dbfil,hb,sizeof(hb),nread);
    for j:=0 to 10 do if hb[j]>32 then fname[i]:=fname[i]+uppercase(char(hb[j]));
    ftyp[i]:=hb[11];
    flen[i]:=hb[16];
    fdec[i]:=hb[17];
    fdisp[i]:=posfr;
    posfr:=posfr+flen[i];
    pwriteln(1,'Field '+inttostr(i)+': '+fname[i]+'   '+char(ftyp[i])+inttostr(flen[i])+'.'+inttostr(fdec[i]));
  end;

{read last header byte}
  blockread(dbfil,b,sizeof(b),nread);

 end;
end;


{////Procedure to write header record information}
procedure writeDBFFileHeader( var dbfil:dbfftype; var dbfhrec:dbfhrecord);
var
b:byte; i,j,posfr,nwrit:integer; hb:array[0..31] of byte;
y,m,d:word;

begin
 with dbfhrec do begin
{reset to beginning of file}
  seek(dbfil,0);
{set first 32 bytes and write to file}
  for j:=0 to 31 do hb[j]:=0;
{file type}
  hb[0]:=3;
{date}
  decodedate(now,y,m,d);
  hb[1]:=y-2000; {year}
  hb[2]:=m;  {month}
  hb[3]:=d;  {day}
{number of records}
  hb[4]:=nrecs mod 256;
  hb[5]:=(nrecs div 256) mod 256;
  hb[6]:=(nrecs div (256*256)) mod 256;
  hb[7]:=(nrecs div (256*256*256)) mod 256;
{header length}
  hb[8]:=(32*(nflds+1)+1) mod 256;
  hb[9]:=(32*(nflds+1)+1) div 256;
{record length}
  hb[10]:=recln mod 256;
  hb[11]:=recln div 256;
{file completeness status}
  hb[12]:=filestat;
{hh sampling rate HHSRAT}
  hb[13]:=hhsrat mod 256;
  hb[14]:=(hhsrat div 256) mod 256;
  hb[15]:=(hhsrat div (256*256)) mod 256;
  hb[16]:=(hhsrat div (256*256*256)) mod 256;
{hh beginning of sample HHSBEG}
  hb[17]:=hhsbeg mod 256;
  hb[18]:=(hhsbeg div 256) mod 256;
  hb[19]:=(hhsbeg div (256*256)) mod 256;
  hb[20]:=(hhsbeg div (256*256*256)) mod 256;
{write}
  blockwrite(dbfil,hb,sizeof(hb),nwrit);

{for each field, set 32 bytes and write to file}
  for i:=1 to nflds do begin
    for j:=0 to 31 do hb[j]:=0;
{field name}
    for j:=1 to length(fname[i]) do hb[j-1]:=ord(fname[i][j]);
{field type}
    hb[11]:=ftyp[i];
{field length}
    hb[16]:=flen[i];
{field decimals}
    hb[17]:=fdec[i];
{write}
    blockwrite(dbfil,hb,sizeof(hb),nwrit);
  end;

{write end of header byte}
  b:=13;
  blockwrite(dbfil,b,sizeof(b),nwrit);
 end;
end;


{//// Procedure to find the index of variable with name s ////}
function DBIndex(dbfhrec:dbfhrecord; s:string):integer;
var i,m:integer; stemp:string;
begin
 with dbfhrec do begin
  stemp:='';
  for i:=1 to length(s) do stemp:=stemp+uppercase(s[i]);
  m:=1;
  while (m<nflds) and (stemp<>fname[m]) do m:=m+1;
  if stemp<>fname[m] then pwriteln(1,'No variable named '+s+' is found in the DBF file');
  dbindex:=m;
 end;
end;

{//// Procedure to get record rnum from the file}
procedure readDBFRecord(var dbfil:dbfftype; var dbfhrec:dbfhrecord; rnum:integer);

var i,j:longint; nread:integer;
begin
 with dbfhrec do begin
  {i:=round(32.0000000*(nflds+1)+(rnum-1.0000000)*recln+1);}
  i:=(32*(nflds+1)+(rnum-1)*recln+1);
  {writeln('seeking at byte ',i,' nflds,rnum,recln = ',nflds,' ',rnum,' ',recln);}
  seek(dbfil,i);
  {$I-} blockread(dbfil,currec,recln,nread); {$I+}
  if ioresult>0 then pwriteln(1,'Error reading DBase record number '+inttostr(rnum));
 end;
end;

{//// Procedure to get an integer value from the current record}
procedure getDBFInt(dbfhrec:dbfhrecord; fnum:integer; var x:integer);
var e,j:integer; s:string;
begin
 with dbfhrec do begin
  setlength(s,flen[fnum]);
  for j:=1 to flen[fnum] do s[j]:=currec[fdisp[fnum]+j];
  {write(s); readln;}
  val(s,x,e);
 end;
end;

{//// Procedure to get a real value from the current record}
procedure getDBFReal(dbfhrec:dbfhrecord; fnum:integer; var x:single);
var e,j:integer; s:string;
begin
 with dbfhrec do begin
  setlength(s,flen[fnum]);
  for j:=1 to flen[fnum] do s[j]:=currec[fdisp[fnum]+j];
  {write(s); readln;}
  val(s,x,e);
 end;
end;

{//// Procedure to put an integer value into the current record}
procedure putDBFInt(var dbfhrec:dbfhrecord; fnum:integer; x:integer);
var e,j:integer; s:string;
begin
 with dbfhrec do begin
  str(x:flen[fnum],s);
  for j:=1 to flen[fnum] do currec[fdisp[fnum]+j]:=s[j];
 end;
end;

{//// Procedure to put a real value into the current record}
procedure putDBFReal(var dbfhrec:dbfhrecord; fnum:integer; x:single);
var e,j:integer; s:string;
begin
 with dbfhrec do begin
  str(x:flen[fnum]:fdec[fnum],s);
  for j:=1 to flen[fnum] do currec[fdisp[fnum]+j]:=s[j];
 end;
end;

{//// Procedure to write the current record to the file}
procedure writeDBFRecord(var dbfil:dbfftype; dbfhrec:dbfhrecord; rnum:integer);
var i:longint; nwrit:integer;
begin
 with dbfhrec do begin
  {i:=round(32.0*(nflds+1)+(rnum-1.0)*recln+1);}
  i:=(32*(nflds+1)+(rnum-1)*recln+1);
  seek(dbfil,i);
  currec[1]:=char(32);
  {$I-} blockwrite(dbfil,currec,recln,nwrit); {$I+}
  if ioresult>0 then pwriteln(1,'Error writing DBase record number '+inttostr(rnum));
 end;
end;

{//// Procedure to write end-of-file character}
procedure writeDBFFileEOF(var dbfil:dbfftype);
var b:byte; nwrit:integer;
begin
  b:=26;
  blockwrite(dbfil,b,sizeof(b),nwrit);
end;

(* code to test the routines
var
  i,j:integer; r,r2:single;
  zonfile,zonfile2:dbfftype;
  zonfhr,zonfhr2:dbfhrecord;
begin
     assign(zonfile,'c:\mab\sacog\daysim\tazdat00.dbf'); reset(zonfile,1);
     readDBFFileHeader (zonfile,zonfhr);
     readDBFFileHeader (zonfile,zonfhr2);
     assign(zonfile2,'c:\mab\sacog\daysim\tazdatxx.dbf'); rewrite(zonfile2,1);
     writeDBFFileHeader (zonfile2,zonfhr2);
     for i:=1 to zonfhr.nrecs do begin
       readDBFRecord(zonfile,zonfhr,i);
       for j:=1 to 41 do begin
         getDBFReal(zonfhr,j,r);
         putDBFReal(zonfhr2,j,r);
       end;
       writeDBFRecord(zonfile2,zonfhr2,i);
     end;
     writeDBFFileEOF(zonfile2);
     writeDBFFileHeader (zonfile2,zonfhr2);
     close(zonfile);
     close(zonfile2);

     assign(zonfile,'daysim\tazdat00.dbf'); reset(zonfile,1);
     readDBFFileHeader (zonfile,zonfhr);
     assign(zonfile2,'daysim\tazdatxx.dbf'); reset(zonfile2,1);
     readDBFFileHeader (zonfile2,zonfhr2);
     for i:=zonfhr.nrecs downto 1 do begin
       readDBFRecord(zonfile,zonfhr,i);
       readDBFRecord(zonfile2,zonfhr2,i);
       for j:=1 to 41 do begin
         getDBFReal(zonfhr,j,r);
         getDBFReal(zonfhr2,j,r2);
         write(i:4,j:4,r:8:0,r2:8:0); readln;
       end;
     end;
     close(zonfile);
     close(zonfile2);
end.
*)
{//////////////// end of routines to read and write dBase IV files ////////////}

{ ====================================================================== }
 { Declarations and procedure to read parcel data and create indices}

 {Global variables}
const
   maxncels=2000000;   // maximum total number of cels
   nlusevars=14;
   nparktypes=2;
type
 celint  = array[1..maxncels] of integer;
 celreal = array[1..maxncels] of single;


var
(* parcel variables *)
   PARCELID :CelInt ;
   XCOORD_P :CelReal ;
   YCOORD_P :CelReal ;
   SQFT_P   :CelReal ;
   TAZ_P    :CelInt ;
   TYPE_P   :CelInt ;
   LUSE_P   :Array[1..nlusevars] of CelReal; {housing, students, employment in single array for easier processing}
   PARKSP_P :Array[1..nparktypes] of CelReal;  {parking spaces of 2 types in single array}
   PARKPR_P :Array[1..nparktypes] of CelReal;  {parking prices of 2 types in single array}
   nparcels:integer;

procedure readParcelData;

var
   i,j,k:integer;
   dbfil:dbfftype;
   dbfhr:dbfhrecord;
   txfil:text;

begin
 if parcelftype=1 then begin
   openDBFFile(dbfil,inputdir+parcelfname,1);
   readDBFFileHeader (dbfil,dbfhr);
   nparcels:=dbfhr.nrecs;

   i:=0;
   repeat
     i:=i+1;
     if i mod 10000=0 then write(i:8);

{read dBase file record}
     readDBFRecord(dbfil,dbfhr,i);

     j:=17; getDBFInt (dbfhr,j, PARCELID[i]);
     j:=16; getDBFReal(dbfhr,j, XCOORD_P[i]);
     j:=8; getDBFReal(dbfhr,j, YCOORD_P[i]);
     j:=3; getDBFReal(dbfhr,j, SQFT_P[i]);
     j:=11; getDBFInt (dbfhr,j, TAZ_P[i]);
     j:=14; getDBFInt (dbfhr,j, TYPE_P[i]);

       for k:=1 to nlusevars do begin
       j:=j+1; getDBFReal(dbfhr,j, LUSE_P[k][i]);
     end;
     for k:=1 to nparktypes do begin
       j:=j+1; getDBFReal(dbfhr,j, PARKSP_P[k][i]);
     end;
     for k:=1 to nparktypes do begin
       j:=j+1; getDBFReal(dbfhr,j, PARKPR_P[k][i]);
     end;
     for k:=1 to nlusevars do begin
     j:=19; getDBFReal(dbfhr,j, LUSE_P[k][i]);  {HHP}
     j:=9; getDBFReal(dbfhr,j, LUSE_P[k][i]);   {STUDK8_P}
     j:=7; getDBFReal(dbfhr,j, LUSE_P[k][i]);   {STUHGH_P}
     j:=20; getDBFReal(dbfhr,j, LUSE_P[k][i]);   {STUUNI_P}
     j:=13; getDBFReal(dbfhr,j, LUSE_P[k][i]);    {EMPEDU_P}
     j:=21; getDBFReal(dbfhr,j, LUSE_P[k][i]);    {EMPFOOD_P}
     j:=23; getDBFReal(dbfhr,j, LUSE_P[k][i]);  {EMPGOV_P}
     j:=12; getDBFReal(dbfhr,j, LUSE_P[k][i]);  {EMPIND_P}
     j:=15; getDBFReal(dbfhr,j, LUSE_P[k][i]);   {EMPMED_P}
     j:=2; getDBFReal(dbfhr,j, LUSE_P[k][i]);  {EMPOFC_P}
     j:=1; getDBFReal(dbfhr,j, LUSE_P[k][i]);  {EMPRET_P}
     j:=10; getDBFReal(dbfhr,j, LUSE_P[k][i]); {EMPSVC_P}
     j:=16; getDBFReal(dbfhr,j, LUSE_P[k][i]);  {EMPRSC_P}
     j:=22; getDBFReal(dbfhr,j, LUSE_P[k][i]); {EMPTOT_P}

     j:=4; getDBFReal(dbfhr,j, PARKSP_P[k][i]);  {PARKDY_P}
     j:=18; getDBFReal(dbfhr,j, PARKSP_P[k][i]); {PARKHR_P}

     j:=5; getDBFReal(dbfhr,j, PARKPR_P[k][i]);  {PPRICDYP}
     j:=24; getDBFReal(dbfhr,j, PARKPR_P[k][i]);   {PPRICHRP}
     end;

     {adjustments - min parcel size}
     if sqft_p[i]<100.0 then sqft_p[i]:=100.0;

   until (i>=nparcels);

   pwriteln(1,inttostr(i)+' records read from '+parcelfname);
   close(dbfil);
 end else
 if parcelftype=2 then begin
   openTextFile(txfil,inputdir+parcelfname,1);
   readln(txfil); {header}
   i:=0;
   repeat
     i:=i+1;
     if i mod 10000=0 then write(i:8);

{read ascii file record}
     read(txfil,PARCELID[i],
                XCOORD_P[i],
                YCOORD_P[i],
                SQFT_P[i],
                TAZ_P[i],
                TYPE_P[i]);
     for k:=1 to nlusevars do read(txfil,LUSE_P[k][i]);

     for k:=1 to nparktypes do read(txfil,PARKSP_P[k][i]);

     for k:=1 to nparktypes do read(txfil,PARKPR_P[k][i]);

     {adjustments - min parcel size}
     if sqft_p[i]<100.0 then sqft_p[i]:=100.0;

     readln(txfil);

   until eof(txfil);
   nparcels:=i;

   pwriteln(1,inttostr(i)+' records read from '+parcelfname);
   close(txfil);
 end;

end;


{ ====================================================================== }
 { Declarations and procedure to read street node data and create indices}

const
   maxnodes=400000;   // maximum total number of nodes
   maxnodeid = 9999999;
type
   nodeint  = array[1..maxnodes] of integer;
   nodereal = array[1..maxnodes] of single;

var
(* node variables *)
   NODEID   :NodeInt ;
   XCOORD_N :NodeReal ;
   YCOORD_N :NodeReal ;
   TOTALLU_N:NodeReal ;
   SQFT_N   :NodeReal ;
   LUSE_N   :Array[1..nlusevars] of NodeReal; {housing, students, employment in single array for easier processing}
   PARKSP_N :Array[1..nparktypes] of NodeReal;  {parking spaces of 2 types in single array}
   PARKPR_N :Array[1..nparktypes] of NodeReal;  {parking prices of 2 types in single array}
   NODES1_N,NODES3_N,NODES4_N:NodeReal;
   nnodes:integer;
   nodeord:array[1..maxnodeid] of integer;

procedure readNodeData;

var
   i,j,k,error:integer;
   dbfil:dbfftype;
   dbfhr:dbfhrecord;
   txfil:text;
begin
   {$I-} assign(txfil,outdir+'psrc_nodes_extended.dat'); reset(txfil); error:=IOresult; {$I+}
   if error=0 then begin
     nodeftype:=3;
     readln(txfil); {header}
     i:=0;
     repeat
       i:=i+1;
       if i mod 10000=0 then write(i:8);
    {read ascii file record with extra land use info from nearest parcels}
       read(txfil,NODEID[i],
                  XCOORD_N[i],
                  YCOORD_N[i],
                  SQFT_N[i],
                  TOTALLU_N[i]);

       for k:=1 to nlusevars do read(txfil,LUSE_N[k][i]);

       for k:=1 to nparktypes do read(txfil,PARKSP_N[k][i]);

       for k:=1 to nparktypes do read(txfil,PARKPR_N[k][i]);

       readln(txfil,
                NODES1_N[i],
                NODES3_N[i],
                NODES4_N[i]);
     until eof(txfil);
     nnodes:=i;
     pwriteln(1,inttostr(i)+' records read from '+nodefname);
     close(txfil);
   end else
   if nodeftype=1 then begin
     openDBFFile(dbfil,inputdir+nodefname,1);
     readDBFFileHeader (dbfil,dbfhr);
     nnodes:=dbfhr.nrecs;

     i:=0;
     repeat
       i:=i+1;
       if i mod 10000=0 then write(i:8);

  {read dBase file record}
       readDBFRecord(dbfil,dbfhr,i);

       j:=  1; getDBFInt (dbfhr,j, NODEID[i]);
       j:=j+1; getDBFReal(dbfhr,j, XCOORD_N[i]);
       j:=j+1; getDBFReal(dbfhr,j, YCOORD_N[i]);

     until (i>=nnodes);

     pwriteln(1,inttostr(i)+' records read from '+nodefname);
     close(dbfil);
   end else
   if nodeftype=2 then begin
     openTextFile(txfil,inputdir+nodefname,1);
     readln(txfil); {header}
     i:=0;
     repeat
       i:=i+1;
       if i mod 10000=0 then write(i:8);

    {read ascii file record}
       read(txfil,NODEID[i],
                  XCOORD_N[i],
                  YCOORD_N[i]);
       readln(txfil);
     until eof(txfil);
     nnodes:=i;
     pwriteln(1,inttostr(i)+' records read from '+nodefname);
     close(txfil);
   end;
   {set ordinal id indexing}
   for i:=1 to maxnodeid do nodeord[i]:=0;
   for i:=1 to nnodes do nodeord[nodeid[i]]:=i;
end;


{ ====================================================================== }

var
 currNodeOrd,nextNodeOrd:integer;
 NNDistance:array[1..maxnodes] of single; nnfile:text;
 nindfile:text; ndisfile:file of integer;
 writeNNfiles:boolean;
 onodeswritten:integer=0;
 dnodeswritten:integer=0;
 onodefirstrec:integer=0;
 onodelastrec:integer=0;

procedure openNodeNodeDistanceFile;
var i,error:integer;
begin
  assign(nnfile,inputdir+circuityfname); reset(nnfile); readln(nnfile);
  pwriteln(1,' Reading node-node distance information from '+circuityfname);
  currNodeOrd:=0;
  repeat
    read(nnfile,i);
    if (i<=0) or (nodeOrd[i]<=0) then readln(nnfile);
  until (i>0) and (nodeOrd[i]>0);
  nextNodeOrd:=nodeOrd[i];
 {$I-} assign(nindfile,outdir+'psrc_node_node_index.dat'); reset(nindfile); error:=IOresult; {$I+}
  if error=0 then writeNNfiles:=false else begin
    writeNNfiles:=true;
    rewrite(nindfile);
    writeln(nindfile,'node_Id',dlm,'firstrec',dlm,'lastrec'); {header}
    assign(ndisfile,outdir+'psrc_node_node_distances_binary.dat'); rewrite(ndisfile);
  end;
end;

procedure closeNodeNodeDistanceFile  ;
begin
  {close binary file}
  close(nnfile);
  if writeNNfiles then begin
    close(nindfile);
    close(ndisfile);
  end;
end;

procedure getNodeNodeDistances(index:integer);
var onode,dnode,dnodeOrd,idist:integer; dist:single;
begin
  while index>currNodeOrd do begin {get next record}
    for dnode:=1 to maxnodes do NNDistance[dnode]:=-1;
    currNodeOrd:=nextNodeOrd;
    onodefirstrec:=0;
    onodelastrec:=0;
    repeat
      readln(nnfile,dnode,dist);
      if (nodeOrd[dnode]>0) and (dist<99.0) then begin
        dNodeOrd:=nodeOrd[dnode];
        NNDistance[dNodeOrd]:=dist*5280;
        if (writeNNfiles) and (currNodeOrd<=dNodeOrd) then begin
          idist:=round(NNDistance[dNodeOrd]);
          write(ndisfile,dnodeOrd,idist);
          dnodeswritten:=dnodeswritten+1;
          if onodefirstrec=0 then onodefirstrec:=dnodeswritten;
          onodelastrec:=dnodeswritten;
          {write('D Record:',dnodeswritten,'= ',dnodeord,' ',dist:6:2,' First/last= ',onodefirstrec,' ',onodelastrec); readln;}
         end;
      end;
      if eof(nnfile) then nextNodeOrd:=nnodes+1 else begin
        read(nnfile,onode);
        nextNodeOrd:=nodeOrd[onode];
      end;
    until (nextNodeOrd>currNodeOrd);
    if (writeNNfiles) then begin
      writeln(nindfile,currNodeOrd,dlm,onodefirstrec,dlm,onodelastrec);
      onodeswritten:=onodeswritten+1;
      {write('O Record:',onodeswritten,'= ',currnodeord,' First/last= ',onodefirstrec,' ',onodelastrec); readln;}
      for onode:=currNodeOrd+1 to nextNodeOrd-1 do begin
        writeln(nindfile,onode,dlm,0,dlm,0);
        onodeswritten:=onodeswritten+1;
      end;
    end;
  end;
end;

function NodeNodeDistance(n1,n2:integer):single;
begin
  if (n1=currNodeOrd) and (n2>0) then begin
    if n1<3 then writeln(prtf,'Nodes :',currnodeOrd:6,' ',nodeId[currNodeOrd]:7,' ',n2:6,' ',nodeId[n2]:7,' ',NNDistance[n2]:8:0);
    NodeNodeDistance:=NNDistance[n2];
  end
  else NodeNodeDistance:=-1;
end;


{ ---------------------------------------------------------------------- }

{ Declarations and procedure to read intersection data and create indices}

 {Global variables}

const maxIntsecs = 199999;

var
  LINKS_I:array[1..maxIntsecs] of integer;
  XCOORD_I:array[1..maxIntsecs] of single;
  YCOORD_I:array[1..maxIntsecs] of single;
   nintsecs:integer;

procedure readIntsecData;

var
   i,j,k:integer;
   dbfil:dbfftype;
   dbfhr:dbfhrecord;
   txfil:text;

begin
 if intsecftype=1 then begin
   openDBFFile(dbfil,inputdir+intsecfname,1);
   readDBFFileHeader (dbfil,dbfhr);
   nintsecs:=dbfhr.nrecs;

   i:=0;
   repeat
     i:=i+1;
     if i mod 10000=0 then write(i:8);

{read dBase file record}
     readDBFRecord(dbfil,dbfhr,i);

     j:=  1; {id not used}
     j:=j+1; getDBFInt (dbfhr,j, LINKS_I[i]);
     j:=j+1; getDBFReal(dbfhr,j, XCOORD_I[i]);
     j:=j+1; getDBFReal(dbfhr,j, YCOORD_I[i]);
   until (i>=nintsecs);

   pwriteln(1,inttostr(i)+' records read from '+intsecfname);
   close(dbfil);
 end else
 if intsecftype=2 then begin
   openTextFile(txfil,inputdir+intsecfname,1);
   readln(txfil); {header}
   i:=0;
   repeat
     i:=i+1;
     if i mod 10000=0 then write(i:8);

{read ascii file record}
     read(txfil,j, {id not used}
                LINKS_I[i],
                XCOORD_I[i],
                YCOORD_I[i]);
     readln(txfil);

   until eof(txfil);
   nintsecs:=i;

   pwriteln(1,inttostr(i)+' records read from '+intsecfname);
   close(txfil);
 end else
   nintsecs:=0;
end;


{ ---------------------------------------------------------------------- }

{ Declarations and procedure to read transit stop data and create indices}

 {Global variables}

const maxStops = 19999;

var
  MODE_S:array[1..maxStops] of integer;
  XCOORD_S:array[1..maxStops] of single;
  YCOORD_S:array[1..maxStops] of single;
  nstops:integer;

procedure readStopData;

var
   i,j,k:integer;
   dbfil:dbfftype;
   dbfhr:dbfhrecord;
   txfil:text;

begin
 if trnstpftype=1 then begin
   openDBFFile(dbfil,inputdir+trnstpfname,1);
   readDBFFileHeader (dbfil,dbfhr);
   nstops:=dbfhr.nrecs;

   i:=0;
   repeat
     i:=i+1;
     if i mod 10000=0 then write(i:8);

{read dBase file record}
     readDBFRecord(dbfil,dbfhr,i);

     j:=  1; {id not used}
     j:=j+1; getDBFInt (dbfhr,j, MODE_S[i]);
     j:=j+1; getDBFReal(dbfhr,j, XCOORD_S[i]);
     j:=j+1; getDBFReal(dbfhr,j, YCOORD_S[i]);
   until (i>=nstops);

   pwriteln(1,inttostr(i)+' records read from '+trnstpfname);
   close(dbfil);
 end else
 if trnstpftype=2 then begin
   openTextFile(txfil,inputdir+trnstpfname,1);
   readln(txfil); {header}
   i:=0;
   repeat
     i:=i+1;
     if i mod 10000=0 then write(i:8);

{read ascii file record}
     read(txfil,j, {id not used}
                MODE_S[i],
                XCOORD_S[i],
                YCOORD_S[i]);
     readln(txfil);

   until eof(txfil);
   nstops:=i;

   pwriteln(1,inttostr(i)+' records read from '+trnstpfname);
   close(txfil);
 end else
   nstops:=0;

end;

{ ---------------------------------------------------------------------- }

{ Declarations and procedure to read open space data and create indices}


function min(a,b:single):single;
begin
  if a<b then min:=a else min:=b;
end;

 {Global variables}

const maxParks = 1999999;

var
  XCOORD_O:array[1..maxParks] of single;
  YCOORD_O:array[1..maxParks] of single;
  SQFT_O:array[1..maxParks] of single;
  nparks:integer;

procedure readParkData;

var
   i,j,k:integer;
   dbfil:dbfftype;
   dbfhr:dbfhrecord;
   txfil:text;

begin
 if opnspcftype=1 then begin
   openDBFFile(dbfil,inputdir+opnspcfname,1);
   readDBFFileHeader (dbfil,dbfhr);
   nparks:=dbfhr.nrecs;

   i:=0;
   repeat
     i:=i+1;
     if i mod 10000=0 then write(i:8);

{read dBase file record}
     readDBFRecord(dbfil,dbfhr,i);

     j:=  1; {id not used}
     j:=j+1; getDBFReal(dbfhr,j, XCOORD_O[i]);
     j:=j+1; getDBFReal(dbfhr,j, YCOORD_O[i]);
     j:=j+1; getDBFReal(dbfhr,j, SQFT_O[i]);

     {adjustments - min parcel size}
     if sqft_o[i]<100.0 then sqft_o[i]:=100.0;

   until (i>=nparks);

   pwriteln(1,inttostr(i)+' records read from '+opnspcfname);
   close(dbfil);

 end else
 if opnspcftype=2 then begin
   openTextFile(txfil,inputdir+opnspcfname,1);
   readln(txfil); {header}
   i:=0;
   repeat
     i:=i+1;
     if i mod 10000=0 then write(i:8);

{read ascii file record}
     read(txfil,j, {id not used}
                XCOORD_O[i],
                YCOORD_O[i],
                SQFT_O[i]);
     readln(txfil);

   until eof(txfil);
   nparks:=i;

   pwriteln(1,inttostr(i)+' records read from '+opnspcfname);
   close(txfil);
 end else
   nparks:=0;

end;

var
NODEIND_P : celint;
NODEIND_I : array[1..maxIntsecs] of integer;
NODEIND_S : array[1..maxStops] of integer;
NODEIND_O : array[1..maxParks] of integer;

procedure CreateNearestNodeCorrespondences;

function NearestNode(x,y:single):integer;
var ndist,idist:single; i,nindex:integer;
begin
  ndist:=999999999999;
  nindex:=0;
  for i:=1 to nnodes do begin
    idist:= sqrt((x-XCOORD_N[i])*(x-XCOORD_N[i]) + (y-YCOORD_N[i])*(y-YCOORD_N[i]));
    if idist<ndist then begin
      ndist:=idist;
      nindex:=i;
    end;
  end;
  NearestNode:=nindex;
end;

var i,j,k,n,p,error:integer; txfil:text;
begin
  timestring:=DateTimetoStr(now);
  pwriteln(1,'Start creating node correspondences at '+timestring);

  {$I-} assign(txfil,outdir+'psrc_parcel_nodes.dat'); reset(txfil); error:=IOresult; {$I+}
  if error=0 then begin
    readln(txfil);
    for i:=1 to nparcels do begin
      if i mod 10000=0 then write(i:8);
      readln(txfil,j,nodeind_p[i]);
    end;
    writeln(nparcels:8);
    close(txfil);
  end else begin
    for i:=1 to nparcels do begin
       if i mod 10000=0 then write(i:8);
       NODEIND_P[i]:= NearestNode(XCOORD_P[i],YCOORD_P[i]);
    end;
    writeln(nparcels:8);
    rewrite(txfil);
    writeln(txfil,'id',dlm,'node_id');
    for i:=1 to nparcels do
      writeln(txfil,parcelid[i],dlm,nodeind_p[i]);
    close(txfil);
  end;

 {$I-} assign(txfil,outdir+'psrc_intsec_nodes.dat'); reset(txfil);  error:=Ioresult; {$I+}
  if error=0 then begin
    readln(txfil);
    for i:=1 to nintsecs do begin
      if i mod 10000=0 then write(i:8);
      readln(txfil,j,nodeind_i[i]);
    end;
    writeln(nintsecs:8);
    close(txfil);
  end else begin
    for i:=1 to nintsecs do begin
       if i mod 10000=0 then write(i:8);
       NODEIND_I[i]:= NearestNode(XCOORD_I[i],YCOORD_I[i]);
    end;
    writeln(nintsecs:8);
    rewrite(txfil);
    writeln(txfil,'id',dlm,'node_id');
    for i:=1 to nintsecs do
      writeln(txfil,i,dlm,nodeind_i[i]);
    close(txfil);
  end;

 {$I-} assign(txfil,outdir+'psrc_tstop_nodes.dat'); reset(txfil);  error:=Ioresult; {$I+}
  if error=0 then begin
    readln(txfil);
    for i:=1 to nstops do begin
      if i mod 10000=0 then write(i:8);
      readln(txfil,j,nodeind_s[i]);
    end;
    writeln(nstops:8);
    close(txfil);
  end else begin
    for i:=1 to nstops   do begin
       if i mod 10000=0 then write(i:8);
       NODEIND_S[i]:= NearestNode(XCOORD_S[i],YCOORD_S[i]);
    end;
    writeln(nstops:8);
    rewrite(txfil);
    writeln(txfil,'id',dlm,'node_id');
    for i:=1 to nstops do
      writeln(txfil,i,dlm,nodeind_s[i]);
    close(txfil);
  end;

 {$I-} assign(txfil,outdir+'psrc_ospace_nodes.dat'); reset(txfil);  error:=Ioresult; {$I+}
  if error=0 then begin
    readln(txfil);
    for i:=1 to nparks do begin
      if i mod 10000=0 then write(i:8);
      readln(txfil,j,nodeind_o[i]);
    end;
    writeln(nparks:8);
    close(txfil);
  end else begin
    for i:=1 to nparks   do begin
       if i mod 10000=0 then write(i:8);
       NODEIND_O[i]:= NearestNode(XCOORD_O[i],YCOORD_O[i]);
    end;
    writeln(nparks:8);
    rewrite(txfil);
    writeln(txfil,'id',dlm,'node_id');
    for i:=1 to nparks do
      writeln(txfil,i,dlm,nodeind_o[i]);
    close(txfil);
  end;

  if nodeftype<3 then begin {collapse parcel land use to nodes}
    writeln('Appending parcel and intersection land use to nodes');
    {empty the variables}
    for n:=1 to nnodes do begin
      sqft_n[n]:=0;
      totallu_n[n]:=0;
      for k:=1 to nlusevars do luse_n[k,n]:=0;
      for k:=1 to nparktypes do parksp_n[k,n]:=0;
      for k:=1 to nparktypes do parkpr_n[k,n]:=0;
      nodes1_n[n]:=0;
      nodes3_n[n]:=0;
      nodes4_n[n]:=0;
     end;
    for p:=1 to nparcels do begin
      if p mod 10000=0 then write(p:8);
      n:=nodeind_p[p];
      if n>0 then begin
        sqft_n[n]:=sqft_n[n]+sqft_p[p];
        for k:=1 to nlusevars do begin luse_n[k,n]:=luse_n[k,n]+luse_p[k,p]; totallu_n[n]:=totallu_n[n]+luse_p[k,p]; end;
        for k:=1 to nparktypes do begin parksp_n[k,n]:=parksp_n[k,n]+parksp_p[k,p]; totallu_n[n]:=totallu_n[n]+parksp_p[k,p]; end;
        for k:=1 to nparktypes do parkpr_n[k,n]:=parkpr_n[k,n]+parkpr_p[k,p]*parksp_p[k,p];
      end;
    end;
    writeln(nparcels:8);
    for i:=1 to nintsecs do begin
      if i mod 10000=0 then write(i:8);
      n:=nodeind_i[i];
      if n>0 then begin
           if links_i[i]=1 then nodes1_n[n]:=nodes1_n[n] + 1 else
           if links_i[i]=3 then nodes3_n[n]:=nodes3_n[n] + 1 else
           if links_i[i]>3 then nodes4_n[n]:=nodes4_n[n] + 1;
           totallu_n[n]:=totallu_n[n]+1;
      end;
    end;
    writeln(nintsecs:8);

    writeln('Writing extended node file');
    assign(txfil,outdir+'psrc_nodes_extended.dat'); rewrite(txfil);
    writeln(txfil,
     'nodeid',dlm,'xcoord_n',dlm,'ycoord_n',dlm,'sqft_n',dlm,'totallu_n',dlm,
     'hh_n',dlm,'stugrd_n',dlm,'stuhgh_n',dlm,'stuuni_n',dlm,
     'empedu_n',dlm,'empfoo_n',dlm,'empgov_n',dlm,'empind_n',dlm,'empmed_n',dlm,'empofc_n',dlm,'empret_n',dlm,'empsvc_n',dlm,'empoth_n',dlm,'emptot_n',dlm,
     'parkdy_n',dlm,'parkhr_n',dlm,'ppricdyn',dlm,'pprichrn',dlm,'nodes1_n',dlm,'nodes3_n',dlm,'nodes4_n');
    for n:=1 to nnodes do begin
      if n mod 10000=0 then write(n:8);
      write(txfil,nodeid[n],dlm,xcoord_n[n]:1:0,dlm,ycoord_n[n]:1:0,dlm,sqft_n[n]:1:0,dlm,totallu_n[n]:4:2);
      for k:=1 to nlusevars do write(txfil,dlm,luse_n[k,n]:4:2);
      for k:=1 to nparktypes do write(txfil,dlm,parksp_n[k,n]:4:2);
      for k:=1 to nparktypes do write(txfil,dlm,parkpr_n[k,n]/(parksp_n[k,n]+0.000000001):4:2); {use average price};
      writeln(txfil,
        dlm,nodes1_n[n]:4:2,
        dlm,nodes3_n[n]:4:2,
        dlm,nodes4_n[n]:4:2);
    end;
    writeln(nnodes:8);
    close(txfil);
  end;
end;

function PathagDist (x1,y1,x2,y2:single) :single;
{calculate pathagorean distance to the nearest foot}
begin
   PathagDist := sqrt( (x1-x2)*(x1-x2) + (y1-y2)*(y1-y2) );
end;


const nbuffers=2; maxfeet = 52800;

var DDecayWeights:array[1..nbuffers,0..maxfeet] of single;

procedure PrecalculateDistanceDecayWeights;
{set buffer weights for both buffers}
var xydist:integer;
begin
  {pre-calculate buffer weights for each foot of distance}
  for xydist:=0 to round(buffdlimit) do begin
      if bufftype1=2 then
        DDecayWeights[1,xydist]:=min(1.0, (1.0 + exp(buffdecay1 * -0.5 + buffoffset1/5280)) / (1.0 + exp(buffdecay1 *(xydist/buffdist1 -0.5 - buffoffset1/5280)))) {logistic decay - inflection at buffdist1}
      else if bufftype1=3 then
        DDecayWeights[1,xydist]:=  exp(buffexpon1 * xydist/5280); {exponential decay}

      if bufftype2=2 then
        DDecayWeights[2,xydist]:=min(1.0, (1.0 + exp(buffdecay2 * -0.5 + buffoffset2/5280)) / (1.0 + exp(buffdecay2 *(xydist/buffdist2 -0.5 - buffoffset2/5280)))) {logistic decay - inflection at buffdist2}
      else if bufftype2=3 then
        DDecayWeights[2,xydist]:=  exp(buffexpon2 * xydist/5280); {exponential decay}
      {if xydist mod 264 = 0 then begin
        writeln(xydist/5280.0:5:2,DDecayWeights[1,xydist]:8:5,DDecayWeights[2,xydist]:8:5); readln;
      end;}
  end;
end;


type bwarray=array[1..nbuffers] of single;

function BufferWeights (xydist,sqft:single) :bwarray;
{set buffer weights for both buffers}
var dwidth, xydistf, xydistn:single;
begin

       if (bufftype1=1) or (bufftype2=1) then begin
         if sqft>0 then begin
        {approximate distance to near near and far parcel boundaries}
           dwidth:=sqrt(sqft);
           xydistf:=xydist+dwidth/2.0;
           xydistn:=xydist-dwidth/2.0;
          end else begin
           dwidth:=1;
           xydistf:=xydist;
           xydistn:=xydist;
         end;
       end;

       if (bufftype1>1) then
         BufferWeights[1]:= DDecayWeights[1,round(xydist)]  {decay buffer - use pre-calculated value}
       else
         if (xydistf<=buffdist1) then
         BufferWeights[1]:= 1 {flat buffer - full parcel within limit}
       else
        if (xydistn>buffdist1) then
         BufferWeights[1]:= 0  {flat buffer - full parcel outside limit}
       else
         BufferWeights[1]:= min(1.0,(buffdist1 - xydistn)/ dwidth);  {flat buffer - part of parcel within limit}

       if (bufftype2>1) then
         BufferWeights[2]:= DDecayWeights[2,round(xydist)]  {decay buffer - use pre-calculated value}
       else
       if (xydistf<=buffdist2) then
         BufferWeights[2]:= 1 {flat buffer - full parcel within limit}
       else
       if (xydistn>buffdist2) then
         BufferWeights[2]:= 0  {flat buffer - full parcel outside limit}
       else
         BufferWeights[2]:= min(1.0,(buffdist2 - xydistn)/ dwidth);  {flat buffer - part of parcel within limit}
end;


{ //////////// code for circuity measures ////////// }
const
ndirections=8;
ndistbands=3;
dirlab:array[1..ndirections] of string[2]=('E','NE','N','NW','W','SW','S','SE');

const maxCircValue = 5.0;  defaultCircuityRatio = 1.41;

var circValue:array[1..maxncels,1..ndirections,1..ndistbands] of single;
  XCOORD_C:array[1..maxncels] of single;
  YCOORD_C:array[1..maxncels] of single;

ncircp:integer;


procedure readCircuityData;
var
   i,j,k,parcelid2,direction,distband:integer;
   dbfil:dbfftype;
   dbfhr:dbfhrecord;
   txfil:text;

begin
 if circuityftype=1 then begin
   openDBFFile(dbfil,inputdir+circuityfname,1);
   readDBFFileHeader (dbfil,dbfhr);
   ncircp:=dbfhr.nrecs;
   if (circuityfdiff=0) and (ncircp <> nparcels) then begin writeln('circuity file has wrong number of recordsw ',ncircp,' should be ',nparcels); readln; end;

   i:=0;
   repeat
     i:=i+1;
     if i mod 10000=0 then write(i:8);

{read dBase file record}
     readDBFRecord(dbfil,dbfhr,i);

     j:=  1; getDBFInt(dbfhr,j,  parcelid2);
     if (circuityfdiff=0)and (parcelid2 <> parcelid[i]) then begin writeln('parcel ',i,' on circuity file has wrong id ',parcelid2,' should be ',parcelid[i]); readln; end;

     for direction:=1 to ndirections do
     for distband:=1 to ndistbands do begin
       j:=j+1; getDBFReal(dbfhr,j, circValue[i,direction,distband]);
       if circValue[i,direction,distband]>maxCircValue then circValue[i,direction,distband]:=maxCircValue ;
     end;
     if circuityfdiff>0 then begin
       j:=j+1; getDBFReal(dbfhr,j, XCOORD_C[i]);
       j:=j+1; getDBFReal(dbfhr,j, YCOORD_C[i]);
     end;
   until (i>=ncircp);

   pwriteln(1,inttostr(i)+' records read from '+opnspcfname);
   close(dbfil);

 end else
 if circuityftype=2 then begin
   openTextFile(txfil,inputdir+circuityfname,1);
   readln(txfil); {header}
   i:=0;
   repeat
     i:=i+1;
     if i mod 10000=0 then write(i:8);

{read ascii file record}
    read(txfil,parcelid2);
    if (circuityfdiff=0) and (parcelid2 <> parcelid[i]) then begin writeln('parcel ',i,' on circuity file has wrong id ',parcelid2,' should be ',parcelid[i]); readln; end;

     for direction:=1 to ndirections do
     for distband:=1 to ndistbands do begin
       read(txfil, circValue[i,direction,distband]);
       if circValue[i,direction,distband]>maxCircValue then circValue[i,direction,distband]:=maxCircValue ;
     end;
     if circuityfdiff>0 then begin
        read(txfil,XCOORD_C[i],YCOORD_C[i]);
     end;

     readln(txfil);

   until eof(txfil);
   ncircp:=i;

   pwriteln(1,inttostr(i)+' records read from '+circuityfname);
   close(txfil);
 end else
   ncircp:=0;

end;


const maxCircDist = 10560.0; {only apply circuity multiplier out to 2 miles = 10560 feet}
const distlimit:array[1..ndistbands] of single=(2640.0,5280.0,7920.0);

function circuityDist(p_circ:integer; ox,oy,dx,dy:single):single;

var oddir,oddi2:integer; xydist,angle,circuityRatio:single; dwt:array[1..ndistbands] of single;

{  Octant  dx-ox  dy-oy  Xdif vs. Ydif
  1  E-NE   pos    pos     greater
  2  NE-N   pos    pos     less
  3  N-NW   neg    pos     less
  4  NW-W   neg    pos     greater
  5  W-SW   neg    neg     greater
  6  SW-S   neg    neg     leYass
  7  S-SE   pos    neg     less
  8  SE-E   pos    neg     greater}

begin
 xydist:=PathagDist(ox,oy,dx,dy);
 if (dx=ox) and (dy=oy) then circuityRatio:= 1.0 else
 begin

  if (dy=oy) then begin {due East or West}
     if (dx>ox) then begin {due E}
       oddir:=1; angle:=0;
     end else begin {due W}
       oddir:=5; angle:=0;
     end;
  end else
  if (dx=ox) then begin {due N or S}
     if (dy>oy) then begin {due N}
       oddir:=3; angle:=0;
     end else begin {due S}
       oddir:=7; angle:=0;
     end;
  end else
  if (dy>oy) then begin {towards North}
     if (dx>ox) then begin {NE quadrant}
       if (abs(dx-ox) > abs(dy-oy)) then begin {E-NE}
          oddir := 1; angle:= abs(dy-oy)/abs(dx-ox);
       end else begin {NE-N}
          oddir := 2; angle:= 1.0 - abs(dx-ox)/abs(dy-oy);
       end;
     end else begin
       if (abs(dx-ox) < abs(dy-oy)) then begin {N-NW}
          oddir := 3; angle:= abs(dx-ox)/abs(dy-oy);
       end else begin {NW-W}
          oddir := 4; angle:= 1.0 - abs(dy-oy)/abs(dx-ox);
       end;
     end;
  end else begin {toward South}
     if (dx<ox) then begin {SW quadrant}
       if (abs(dx-ox) > abs(dy-oy)) then begin {W-SW}
          oddir := 5; angle:= abs(dy-oy)/abs(dx-ox);
       end else begin {SW-S}
          oddir := 6; angle:= 1.0 - abs(dx-ox)/abs(dy-oy);
       end;
     end else begin
       if (abs(dx-ox) < abs(dy-oy)) then begin {S-SE}
          oddir := 7; angle:= abs(dx-ox)/abs(dy-oy);
       end else begin {SE-E}
          oddir := 8; angle:= 1.0 - abs(dy-oy)/abs(dx-ox);
       end;
     end;
  end;

  if (xydist<distlimit[1]) then begin dwt[1]:=1.0; dwt[2]:=0; dwt[3]:=0; end else
  if (xydist<distlimit[2]) then begin dwt[2]:=(xydist-distlimit[1])/(distlimit[2]-distlimit[1]); dwt[1]:=1.0-dwt[2]; dwt[3]:=0; end else
  if (xydist<distlimit[3]) then begin dwt[3]:=(xydist-distlimit[2])/(distlimit[3]-distlimit[2]); dwt[2]:=1.0-dwt[3]; dwt[1]:=0; end else
  if (xydist>=distlimit[3]) then begin dwt[3]:=1.0; dwt[2]:=0; dwt[1]:=0; end;

  if oddir<ndirections then oddi2:=oddir+1 else oddi2:=1;

  circuityRatio:=(1-angle) * (dwt[1]*circValue[p_circ,oddir,1] + dwt[2]*circValue[p_circ,oddir,2] + dwt[3]*circValue[p_circ,oddir,3])
               +    angle  * (dwt[1]*circValue[p_circ,oddi2,1] + dwt[2]*circValue[p_circ,oddi2,2] + dwt[3]*circValue[p_circ,oddi2,3]);
 end;
 if xydist<maxCircDist then circuityDist:= circuityRatio * xydist else
                            circuityDist:= circuityRatio * maxCircDist + defaultCircuityRatio * (xydist - maxCircDist); {default ratio, around sqrt(2), applied to portion of distance over maxCircDist}
end;

{Buffer variables}
var
    luse_b:array[1..maxnodes,1..nbuffers,1..nlusevars] of single;
    parksp_b,parkpr_b:array[1..maxnodes,1..nbuffers,1..nparktypes] of single;
    nodes1,nodes3,nodes4,tstops,bparks,aparks:array[1..maxnodes,1..nbuffers] of single;
    dist_tran:array[1..maxnodes,1..5] of single;
    dist_park:array[1..maxnodes] of single;

const tiny=0.0000000000001;

procedure BufferAroundAPoint(originx,originy:real; originIndex,sindex:integer);

function SetDistance(oindex,dindex:integer; ox,oy,dx,dy:real):single;
var xydist:single;
begin
       if circuityftype=3 then begin
          xydist:=NodeNodeDistance(oindex,dindex);
          if xydist<0 then xydist:=1.4 * PathagDist(ox,oy,dx,dy);
       end else
       if circuityftype>0 then xydist:=CircuityDist(oindex,ox,oy,dx,dy)
                          else xydist:=PathagDist         (ox,oy,dx,dy);
       SetDistance:=xydist;
end;

var j,k,n:integer;
   xydist:single; bweight:bwarray; closest:single;

begin
     {initialize parcel buffer measures}
     for j:=1 to nbuffers do begin
       for k:=1 to nlusevars do luse_b[sindex,j,k]:=0;
       for k:=1 to nparktypes do parksp_b[sindex,j,k]:=0;
       for k:=1 to nparktypes do parkpr_b[sindex,j,k]:=0;
     end;

     {initialize intersection buffer measures}
     for j:=1 to nbuffers do begin
       nodes1[sindex,j]:=0;
       nodes3[sindex,j]:=0;
       nodes4[sindex,j]:=0;
     end;

     {initialize transit stop buffer measures}
     for j:=1 to nbuffers do tstops[sindex,j]:=0;
     for k:=1 to 5 do dist_tran[sindex,k]:=999.0;

     {initialize open space buffer measures}
     for j:=1 to nbuffers do begin bparks[sindex,j]:=0; aparks[sindex,j]:=0; end;
     dist_park[sindex]:=999.0;

     if circuityftype<3 then begin
      {loop on all parcels and screen on orthogonal distance less than buffdlimit}
      if originindex<3 then writeln(prtf,'Start of parcels for node ',originindex);

      for n:=1 to nparcels do
      if abs(originx-xcoord_p[n])+abs(originy-ycoord_p[n])<buffdlimit then begin

       {distances}
       {writeln('P ',originindex,' ',n,' ',nodeind_p[n]);}
       xydist:=SetDistance(originIndex,nodeind_p[n],originx,originy,xcoord_p[n],ycoord_p[n]);

       if (xydist<maxfeet) then begin

         bweight:=BufferWeights(xydist,sqft_p[n]);

        {accumulate all buffer variables}
         for j:=1 to nbuffers do if bweight[j]>tiny then begin

           for k:=1 to nlusevars do luse_b[sindex,j,k]:=luse_b[sindex,j,k] + (bweight[j] * luse_p[k,n]);

           for k:=1 to nparktypes do begin
             parksp_b[sindex,j,k]:= parksp_b[sindex,j,k] + (bweight[j] * parksp_p[k,n]);
             parkpr_b[sindex,j,k]:= parkpr_b[sindex,j,k] + (bweight[j] * parksp_p[k,n] * parkpr_p[k,n]); {also weight by number of spaces}
           end;

           {for psrc, add up type 19 parcels in bparks}
           if (type_p[n]=19) and (copy(outfname,1,4)='psrc') and (opnspcftype=0) then bparks[sindex,j]:=bparks[sindex,j] + bweight[j];
         end;
       end;

      end; {parcel loop}
      {loop on all intersections}
      if originindex<3 then writeln(prtf,'Start of intersections for node ',originindex);
      for n:=1 to nintsecs do
      if abs(originx-xcoord_i[n])+abs(originy-ycoord_i[n])<buffdlimit then begin

       {distances}
       {writeln('I ',originindex,' ',n,' ',nodeind_i[n]);}
       xydist:=SetDistance(originIndex,nodeind_i[n],originx,originy,xcoord_i[n],ycoord_i[n]);

       if xydist<maxfeet then begin

         bweight:=BufferWeights(xydist,0);

         {accumulate all buffer variables}
         for j:=1 to nbuffers do if bweight[j]>tiny then begin
           if links_i[n]=1 then nodes1[sindex,j]:=nodes1[sindex,j] + bweight[j] else
           if links_i[n]=3 then nodes3[sindex,j]:=nodes3[sindex,j] + bweight[j] else
           if links_i[n]>3 then nodes4[sindex,j]:=nodes4[sindex,j] + bweight[j];
         end;
       end;

      end; {intersection loop}

    end else begin
     {loop on all nodes and screen on orthogonal distance less than buffdlimit}
      if originindex<3 then writeln(prtf,'Start of nodes for node ',originindex);
      for n:=1 to nnodes do
      if (totallu_n[n]>0) and (abs(originx-xcoord_n[n])+abs(originy-ycoord_n[n])<buffdlimit*1.5) then begin

       {distances}
       {writeln('P ',originindex,' ',n,' ',nodeind_p[n]);}
       xydist:=SetDistance(originIndex,n,originx,originy,xcoord_n[n],ycoord_n[n]);

       if (xydist<maxfeet) then begin

         bweight:=BufferWeights(xydist,sqft_n[n]);

        {accumulate all buffer variables}
         for j:=1 to nbuffers do if bweight[j]>tiny then begin

           for k:=1 to nlusevars do luse_b[sindex,j,k]:=luse_b[sindex,j,k] + (bweight[j] * luse_n[k,n]);

           for k:=1 to nparktypes do begin
             parksp_b[sindex,j,k]:= parksp_b[sindex,j,k] + (bweight[j] * parksp_n[k,n]);
             parkpr_b[sindex,j,k]:= parkpr_b[sindex,j,k] + (bweight[j] * parksp_n[k,n] * parkpr_n[k,n]); {also weight by number of spaces}
           end;
           nodes1[sindex,j]:=nodes1[sindex,j] + bweight[j]*nodes1_n[n];
           nodes3[sindex,j]:=nodes3[sindex,j] + bweight[j]*nodes3_n[n];
           nodes4[sindex,j]:=nodes4[sindex,j] + bweight[j]*nodes4_n[n];
         end;
       end;
      end; {node loop}
     end;



     {loop on all transit stops}
     if originindex<3 then writeln(prtf,'Start of transit stops for node ',originindex);
     for n:=1 to nstops do
     if abs(originx-xcoord_s[n])+abs(originy-ycoord_s[n])<maxfeet then begin

       {distances}
       {writeln('S ',originindex,' ',n,' ',nodeind_s[n]);}
       xydist:=SetDistance(originIndex,nodeind_s[n],originx,originy,xcoord_s[n],ycoord_s[n]);

       if (mode_s[n]>=1) and (mode_s[n]<=5) and (xydist/5280.0<dist_tran[sindex,mode_s[n]]) then
          dist_tran[sindex,mode_s[n]]:=xydist/5280.0;

       if (xydist<buffdlimit) and (xydist<maxfeet) then begin

         bweight:=BufferWeights(xydist,0);

         {accumulate all buffer variables}
         for j:=1 to nbuffers do if bweight[j]>tiny then begin
            tstops[sindex,j]:=tstops[sindex,j] + bweight[j];
         end;

       end;
     end; {stop loop}




     {loop on all park records}
     if originindex<3 then writeln(prtf,'Start of open space for node ',originindex);
     for n:=1 to nparks do
     if (nparks<100000) or (abs(originx-xcoord_o[n])+abs(originy-ycoord_o[n])<buffdlimit) then begin

       {distances}
       {writeln('O ',originindex,' ',n,' ',nodeind_o[n]);}
       xydist:=SetDistance(originIndex,nodeind_o[n],originx,originy,xcoord_o[n],ycoord_o[n]);


       if xydist<maxfeet then begin
           bweight:=BufferWeights(xydist,sqft_o[n]);

           {accumulate all buffer variables}
           for j:=1 to nbuffers do if bweight[j]>tiny then begin
              bparks[sindex,j]:=bparks[sindex,j] + bweight[j];
              aparks[sindex,j]:=aparks[sindex,j] + (bweight[j]*sqft_o[n]);
           end;

           xydist:=xydist - sqrt(sqft_o[n]/3.14); {adjust distance to edge of park, if park were a circle}
           if xydist<0 then xydist:=0;
           if (xydist/5280.0<dist_park[sindex]) then dist_park[sindex]:=xydist/5280.0;
         end;

      end; {park loop}

end;


                                                             
{ ///////////// Main Program ////////// }

var
    p,n,j,k,direction,distband,sindex:integer;
     buffil:text;


Begin
   GetRunControls;
   if outfdelim=1 then dlm:=' ' else
   if outfdelim=2 then dlm:=chr(9) else dlm:=',';

   {load the input data}
   if (circuityftype=3) then begin
     readNodeData;
   end;
   readParcelData;
   readIntsecData;
   readStopData;
   readParkData;
   if (circuityftype=1) or (circuityftype=2) then readCircuityData else
   if (circuityftype=3) then begin
     createNearestNodeCorrespondences;
   end;
   PrecalculateDistanceDecayWeights;

   assign(buffil,outdir+outfname); rewrite(buffil);

   write(buffil,
   'parcelid',dlm,'xcoord_p',dlm,'ycoord_p',dlm,'sqft_p',dlm,'taz_p',dlm,'lutype_p',dlm,
   'hh_p',dlm,'stugrd_p',dlm,'stuhgh_p',dlm,'stuuni_p',dlm,
   'empedu_p',dlm,'empfoo_p',dlm,'empgov_p',dlm,'empind_p',dlm,'empmed_p',dlm,'empofc_p',dlm,'empret_p',dlm,'empsvc_p',dlm,'empoth_p',dlm,'emptot_p',dlm,
   'parkdy_p',dlm,'parkhr_p',dlm,'ppricdyp',dlm,'pprichrp',dlm,
   'hh_1',dlm,'stugrd_1',dlm,'stuhgh_1',dlm,'stuuni_1',dlm,
   'empedu_1',dlm,'empfoo_1',dlm,'empgov_1',dlm,'empind_1',dlm,'empmed_1',dlm,'empofc_1',dlm,'empret_1',dlm,'empsvc_1',dlm,'empoth_1',dlm,'emptot_1',dlm,
   'parkdy_1',dlm,'parkhr_1',dlm,'ppricdy1',dlm,'pprichr1',dlm,
   'nodes1_1',dlm,'nodes3_1',dlm,'nodes4_1',dlm,'tstops_1',dlm,'nparks_1',dlm,'aparks_1',dlm,
   'hh_2',dlm,'stugrd_2',dlm,'stuhgh_2',dlm,'stuuni_2',dlm,
   'empedu_2',dlm,'empfoo_2',dlm,'empgov_2',dlm,'empind_2',dlm,'empmed_2',dlm,'empofc_2',dlm,'empret_2',dlm,'empsvc_2',dlm,'empoth_2',dlm,'emptot_2',dlm,
   'parkdy_2',dlm,'parkhr_2',dlm,'ppricdy2',dlm,'pprichr2',dlm,
   'nodes1_2',dlm,'nodes3_2',dlm,'nodes4_2',dlm,'tstops_2',dlm,'nparks_2',dlm,'aparks_2',dlm,
   'dist_lbus',dlm,'dist_ebus',dlm,'dist_crt',dlm,'dist_fry',dlm,'dist_lrt',dlm,'dist_park');
   if (circuityftype=1) or (circuityftype=2) then
     for direction:=1 to ndirections do for distband:=1 to ndistbands do write(buffil,dlm,'Circ_',dirlab[direction],distband);
   writeln(buffil);

   if circuityftype=3 then begin
    {create buffer measures}
     timestring:=DateTimetoStr(now);
     pwriteln(1,'Start buffering around nodes at '+timestring);
     writeln('Nodes processed ... ');

     {first buffer around every node and store}
     openNodeNodeDistanceFile;
     for n:=1 to nnodes do begin
       if n mod 1000=0 then write(n:8);
       getNodeNodeDistances(n);
       BufferAroundAPoint(xcoord_n[n],ycoord_n[n],n,n);
     end;
     closeNodeNodeDistanceFile;
   end;

   timestring:=DateTimetoStr(now);
   pwriteln(1,'Start writing parcel buffer records at '+timestring);
   writeln('Parcels processed ... ');
  {loop on parcels from parcel file}
   for p:=1 to nparcels do begin

     if p mod 1000=0 then write(p:8);
     if taz_p[p]>0 then begin {don't bother buffering if invalid zone number}

     {if using nodes, just take buffer record from nearest node, else buffer and take from sindex=1}
     if circuityftype=3 then sindex:=nodeind_p[p] else begin
       sindex:=1;
       BufferAroundAPoint(xcoord_p[p],ycoord_p[p],p,sindex);
     end;

     {write record for parcel}

     {first copy existing parcel variables}
      write(buffil,parcelid[p],
      dlm,xcoord_p[p]:1:0,
      dlm,ycoord_p[p]:1:0,
      dlm,sqft_p[p]:1:0,
      dlm,taz_p[p],
      dlm,type_p[p]);
      for k:=1 to nlusevars do write(buffil,dlm,luse_p[k,p]:4:2);
      for k:=1 to nparktypes do write(buffil,dlm,parksp_p[k,p]:4:2);
      for k:=1 to nparktypes do write(buffil,dlm,parkpr_p[k,p]:4:2);

      {then add buffer variables}
      for j:=1 to nbuffers do begin
        for k:=1 to nlusevars do write(buffil,dlm,luse_b[sindex,j,k]:4:2);
        for k:=1 to nparktypes do write(buffil,dlm,parksp_b[sindex,j,k]:4:2);
        for k:=1 to nparktypes do write(buffil,dlm,parkpr_b[sindex,j,k]/(parksp_b[sindex,j,k]+0.000000001):4:2); {use average price}
        write(buffil,
        dlm,nodes1[sindex,j]:4:2,
        dlm,nodes3[sindex,j]:4:2,
        dlm,nodes4[sindex,j]:4:2,
        dlm,tstops[sindex,j]:4:2,
        dlm,bparks[sindex,j]:4:2,
        dlm,aparks[sindex,j]/(bparks[sindex,j]+0.000001):4:0);
      end;

      {write distance variables}
      for k:=1 to 5 do write(buffil,dlm,dist_tran[sindex,k]:4:2);
      write(buffil,dlm,dist_park[sindex]:4:2);

      if (circuityftype=1) or (circuityftype=2) then
        for direction:=1 to ndirections do
        for distband:=1 to ndistbands do write(buffil,dlm,circValue[p,direction,distband]:4:2);

      writeln(buffil);
    end;
   end;
   close(buffil);


   timestring:=DateTimetoStr(now);
   pwriteln(1,'Finish computation of buffers at '+timestring);

   if prtfileopen>0 then close(prtf);

   if waittoexit>0 then begin writeln; write('Press Enter to exit ...'); readln; end;
End.

