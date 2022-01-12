Search.setIndex({docnames:["index","modules","mwr_raw2l1","mwr_raw2l1.measurement","mwr_raw2l1.readers","mwr_raw2l1.utils"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":4,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":3,"sphinx.domains.rst":2,"sphinx.domains.std":2,"sphinx.ext.intersphinx":1,"sphinx.ext.viewcode":1,sphinx:56},filenames:["index.rst","modules.rst","mwr_raw2l1.rst","mwr_raw2l1.measurement.rst","mwr_raw2l1.readers.rst","mwr_raw2l1.utils.rst"],objects:{"":[[2,0,0,"-","mwr_raw2l1"]],"mwr_raw2l1.errors":[[2,1,1,"","CoordinateError"],[2,1,1,"","DimensionError"],[2,1,1,"","FileTooLong"],[2,1,1,"","FileTooShort"],[2,1,1,"","MWRConfigError"],[2,1,1,"","MWRError"],[2,1,1,"","MWRFileError"],[2,1,1,"","MWRInputError"],[2,1,1,"","MWROutputError"],[2,1,1,"","MissingConfig"],[2,1,1,"","MissingDataSource"],[2,1,1,"","MissingInputArgument"],[2,1,1,"","OutputDimensionError"],[2,1,1,"","TimeInputMissing"],[2,1,1,"","TimerefError"],[2,1,1,"","UnknownFileType"],[2,1,1,"","UnknownFlagValue"],[2,1,1,"","WrongFileType"],[2,1,1,"","WrongInputFormat"],[2,1,1,"","WrongNumberOfChannels"]],"mwr_raw2l1.main":[[2,2,1,"","get_meas_constructor"],[2,2,1,"","get_reader"],[2,2,1,"","main"]],"mwr_raw2l1.measurement":[[3,0,0,"-","measurement"],[3,0,0,"-","measurement_helpers"],[3,0,0,"-","rpg_helpers"],[3,0,0,"-","scan_transform"]],"mwr_raw2l1.measurement.measurement":[[3,3,1,"","Measurement"]],"mwr_raw2l1.measurement.measurement.Measurement":[[3,4,1,"","from_attex"],[3,4,1,"","from_radiometrics"],[3,4,1,"","from_rpg"],[3,4,1,"","run"],[3,4,1,"","set_coord"],[3,4,1,"","set_statusflag"]],"mwr_raw2l1.measurement.measurement_helpers":[[3,2,1,"","drop_duplicates"],[3,2,1,"","make_dataset"]],"mwr_raw2l1.measurement.rpg_helpers":[[3,2,1,"","merge_brt_blb"],[3,2,1,"","to_datasets"]],"mwr_raw2l1.measurement.scan_transform":[[3,2,1,"","scan_endtime_to_time"],[3,2,1,"","scan_to_timeseries"],[3,2,1,"","scan_to_timeseries_from_dict"],[3,2,1,"","scantime_from_aux"]],"mwr_raw2l1.readers":[[4,0,0,"-","base_reader_rpg"],[4,0,0,"-","legacy_reader_rpg"],[4,0,0,"-","reader_radiometrics"],[4,0,0,"-","reader_rpg"],[4,0,0,"-","reader_rpg_helpers"]],"mwr_raw2l1.readers.base_reader_rpg":[[4,3,1,"","BaseReader"]],"mwr_raw2l1.readers.base_reader_rpg.BaseReader":[[4,4,1,"","check_data"],[4,4,1,"","decode_binary"],[4,4,1,"","decode_binary_np"],[4,4,1,"","interpret_filecode"],[4,4,1,"","interpret_header"],[4,4,1,"","interpret_raw_data"],[4,4,1,"","read"],[4,4,1,"","run"]],"mwr_raw2l1.readers.legacy_reader_rpg":[[4,2,1,"","read_blb"],[4,2,1,"","read_brt"],[4,2,1,"","read_hkd"],[4,2,1,"","read_irt"],[4,2,1,"","read_met"]],"mwr_raw2l1.readers.reader_radiometrics":[[4,2,1,"","read_header"]],"mwr_raw2l1.readers.reader_rpg":[[4,3,1,"","BLB"],[4,3,1,"","BRT"],[4,3,1,"","HKD"],[4,3,1,"","IRT"],[4,3,1,"","MET"],[4,2,1,"","main"],[4,2,1,"","read_multiple_files"]],"mwr_raw2l1.readers.reader_rpg.BLB":[[4,4,1,"","interpret_filecode"],[4,4,1,"","interpret_header"],[4,4,1,"","interpret_raw_data"],[4,4,1,"","interpret_scanobs"]],"mwr_raw2l1.readers.reader_rpg.BRT":[[4,4,1,"","interpret_filecode"]],"mwr_raw2l1.readers.reader_rpg.HKD":[[4,4,1,"","interpret_filecode"],[4,4,1,"","interpret_raw_data"]],"mwr_raw2l1.readers.reader_rpg.IRT":[[4,4,1,"","interpret_filecode"]],"mwr_raw2l1.readers.reader_rpg.MET":[[4,4,1,"","interpret_filecode"]],"mwr_raw2l1.readers.reader_rpg_helpers":[[4,2,1,"","flag_int2bits"],[4,2,1,"","interpret_angle"],[4,2,1,"","interpret_bit_order"],[4,2,1,"","interpret_coord"],[4,2,1,"","interpret_hkd_contents_code"],[4,2,1,"","interpret_met_auxsens_code"],[4,2,1,"","interpret_quadrant_int"],[4,2,1,"","interpret_scanflag"],[4,2,1,"","interpret_statusflag"],[4,2,1,"","interpret_time"],[4,2,1,"","interpret_tstab_flag"]],"mwr_raw2l1.utils":[[5,0,0,"-","config_utils"],[5,0,0,"-","file_utils"],[5,0,0,"-","transformations"]],"mwr_raw2l1.utils.config_utils":[[5,2,1,"","get_conf"],[5,2,1,"","get_inst_config"],[5,2,1,"","get_nc_format_config"]],"mwr_raw2l1.utils.file_utils":[[5,2,1,"","abs_file_path"],[5,2,1,"","datestr_from_filename"],[5,2,1,"","generate_output_filename"],[5,2,1,"","get_binary"],[5,2,1,"","get_corresponding_pickle"],[5,2,1,"","get_files"],[5,2,1,"","pickle_dump"],[5,2,1,"","pickle_load"]],"mwr_raw2l1.utils.transformations":[[5,2,1,"","timedelta2s"]],"mwr_raw2l1.write_netcdf":[[2,2,1,"","generate_history_str"],[2,2,1,"","prepare_datavars"],[2,2,1,"","prepare_global_attrs"],[2,2,1,"","write"],[2,2,1,"","write_from_dict"],[2,2,1,"","write_from_xarray"]],mwr_raw2l1:[[2,0,0,"-","errors"],[2,0,0,"-","log"],[2,0,0,"-","main"],[3,0,0,"-","measurement"],[4,0,0,"-","readers"],[5,0,0,"-","utils"],[2,0,0,"-","write_netcdf"]]},objnames:{"0":["py","module","Python module"],"1":["py","exception","Python exception"],"2":["py","function","Python function"],"3":["py","class","Python class"],"4":["py","method","Python method"]},objtypes:{"0":"py:module","1":"py:exception","2":"py:function","3":"py:class","4":"py:method"},terms:{"0":[3,4],"01":3,"02":3,"1":[0,3,4],"10":[3,4],"100":4,"1000":4,"17":3,"1st":4,"2":4,"2d":3,"2nd":4,"3":4,"3d":4,"3rd":4,"5":4,"6":4,"case":2,"class":[2,3,4,5],"default":[2,3,4,5],"do":[2,4,5],"float":4,"function":[2,3,4],"int":4,"long":[2,3],"return":[3,4,5],"short":[2,4],"true":2,"var":[2,3,4],"while":4,If:[3,4,5],In:2,It:[0,3],Not:3,The:[3,4],_read_head:4,_read_mea:4,ab:4,abs_file_path:5,absolut:5,accept:4,accept_localtim:4,accord:2,ad:3,add:2,after:[2,5],again:3,all:[3,4],all_data:3,allow:3,alreadi:4,also:4,altitud:[2,3],an:[2,3,4],analog:5,angl:[3,4],ani:[2,3,5],anymor:3,appli:4,approxim:3,ar:[2,3,5],arg:[2,3],argument:[2,3],arrai:[3,4],arrg:3,assign:4,assum:[2,3,5],atmospher:0,attach:3,attr:2,attr_kei:2,attribut:2,augment:4,aux:3,auxiliari:[3,4],auxsenscod:4,avail:[3,4],averag:4,avg:4,azi:4,azimuth:4,b:[],band:0,base:[2,3,4],base_reader_rpg:[1,2],basenam:[4,5],basename_yyyymmddhhmm:5,baseread:4,befor:5,being:2,between:3,binari:[2,4,5],bit:4,bit_ord:4,blb:[2,3,4],bool:[2,4],both:[3,4],bright:4,brt:[3,4],buffer:2,byte_offset:4,byte_ord:4,call:2,can:[2,4,5],care:[2,4],chang:5,channel:2,check:[3,4,5],check_data:4,chosen:2,classmethod:3,code:[0,3,4],collect:3,come:3,common:0,complet:[2,5],conf:[2,5],conf_fil:2,conf_inst:[2,3],conf_nc:2,config:[2,3,5],config_util:[1,2],configur:[0,2,3,4,5],consist:[3,4,5],constructor:[2,3],consum:2,contain:[2,3,4,5],containt:4,content:1,contents_code_integ:4,coordin:[2,3,4],coordinateerror:2,copi:2,copy_data:2,correspond:[2,3,4,5],count:5,creat:2,creation:2,criteria:5,d:3,data:[0,2,3,4,5],data_bin:4,data_in:2,dataarrai:[2,3,5],datafil:[2,3],dataset:[2,3],date:5,datestr_format:5,datestr_from_filenam:5,datetim:[3,4],datetime64:[3,5],ddd:4,dddmm:4,decim:4,decod:4,decode_binari:4,decode_binary_np:4,dedic:0,defin:[0,2],definit:2,degre:[3,4],delta_altitud:3,delta_lat:3,delta_lon:3,descript:4,determin:3,dict:[2,3,4],dictioinari:3,dictionari:[2,3,4,5],differ:[3,4,5],digit:[4,5],dim:3,dimens:[2,3],dimensionerror:2,dims_requir:2,dir_in:5,directori:5,document:[0,4],doe:[2,4],don:[3,4,5],drop:3,drop_dupl:3,ds:3,duplic:3,durat:3,e:[0,2,3,4],each:[3,5],el:[3,4],elev:[3,4],empti:[3,4,5],encod:4,encoding_pattern:4,end:[3,5],endtim:3,entir:[2,5],entri:2,error:[1,3],especi:2,except:[2,3],execut:4,expect:2,experi:2,ext:5,extens:[4,5],f:4,fals:[2,4,5],file:[0,2,3,4,5],file_path:5,file_util:[1,2],filenam:[2,4,5],filename_rawdata:5,filetoolong:2,filetooshort:2,filetyp:[2,3],fill:3,finish:2,first:[4,5],fix:4,flag:[2,4],flag_int2bit:4,flag_integ:4,flat:3,flatten:3,fomrat:4,form:[2,3],format:[0,2,4,5],found:4,fraction:4,frequenc:2,from:[2,3,4,5],from_attex:3,from_radiometr:3,from_rpg:3,full:5,func:[],further:2,g:[2,3,4],gener:[2,3,4,5],generate_history_str:2,generate_output_filenam:5,get:[2,4,5],get_binari:5,get_conf:5,get_corresponding_pickl:5,get_fil:[2,5],get_inst_config:5,get_meas_constructor:2,get_nc_format_config:5,get_read:2,given:[2,5],global:2,goe:2,grid:3,happen:2,hard:3,hatpro:4,have:[3,4],header:4,helper:[2,4],here:2,histori:2,hkd:[3,4],hold:4,housekeep:[3,4],how:2,humid:0,humpro:4,i:4,id:[2,5],identifi:5,ignor:3,includ:[2,3,5],independ:4,index:0,indic:3,individu:4,infer:[3,5],infrar:4,initi:2,input:[2,3,4],inst:5,inst_conf_fil:2,inst_config_fil:2,instanc:[2,3,4],instrument:[0,2,3,5],int_quadr:4,integ:4,integr:3,interpret:4,interpret_angl:4,interpret_bit_ord:4,interpret_coord:4,interpret_filecod:4,interpret_head:4,interpret_hkd_contents_cod:4,interpret_met_auxsens_cod:4,interpret_quadrant_int:4,interpret_raw_data:4,interpret_scanflag:4,interpret_scanob:4,interpret_statusflag:4,interpret_tim:4,interpret_tstab_flag:4,irt:[3,4],item:3,its:2,k:[0,4],kei:[2,3,4],keyword:2,known:2,kwarg:[2,3],l1:4,last:5,lat:3,latitud:[3,4],legaci:2,legacy_read:5,legacy_reader_rpg:[1,2],length:5,level:0,librari:0,list:[3,4,5],local:2,localtim:4,locat:5,log:1,lognitud:4,lon:3,longitud:[3,4],lv0:4,main:[1,4],maintain:2,make:5,make_dataset:3,mandatori:2,match:[2,4],maximum:3,mean:4,measur:[1,2,4],measurement_help:[1,2],merg:3,merge_brt_blb:3,met:4,metadata:4,meteorolog:4,meter:3,method:[2,3],microwav:0,minut:4,mirror:3,miss:[2,3],missingconfig:2,missingdatasourc:2,missinginputargu:2,mm:4,mmmm:4,modif:2,modifi:2,modul:[0,1],more:3,most:0,move:3,multidim_var:3,multipl:4,must:3,mwr:[0,2,3,4],mwrconfigerror:2,mwrerror:2,mwrfileerror:2,mwrinputerror:2,mwroutputerror:2,n_angl:3,n_dims_var:2,n_entri:4,n_freq:[2,4],n_mea:[2,4],name:[2,3,4],nan:[3,4],nativ:0,nc:5,nc_attribut:2,nc_conf_fil:2,nc_format_config_fil:2,ndarrai:[3,4],need:3,netcdf4:2,netcdf:[0,2,5],next:4,none:[2,3,5],note:4,noth:4,np:3,number:[2,3,5],numpi:[3,4,5],ob:[3,4],object:[3,4,5],observ:[0,3,4],ok:4,old:2,one:[3,4],onli:[3,5],operation:0,option:[3,4,5],order:3,origin:2,ot:3,out:4,output:[2,3,4,5],outputdimensionerror:2,over:[2,4],packag:[0,1],page:0,param:5,paramet:[2,3,4,5],part:5,pass:[2,3],path:[2,4,5],path_pickl:5,per:3,permit:5,pick:2,pickl:5,pickle_dump:5,pickle_load:5,place:2,placehold:3,point:4,preced:3,prepar:2,prepare_datavar:2,prepare_global_attr:2,present:3,previou:5,primary_src:3,procedur:4,process:[0,2],profil:0,project:5,provid:3,python:0,quadrant:4,radiomet:[0,4],rain:4,rainflag:4,rais:[2,3],rang:2,raw:[2,5],re:3,read:[0,2,3,4,5],read_blb:4,read_brt:4,read_head:4,read_hkd:4,read_in_data:3,read_irt:4,read_met:4,read_multiple_fil:4,reader:[1,2],reader_radiometr:[1,2],reader_rpg:[1,2],reader_rpg_help:[1,2],readin_data:3,refer:2,rel:5,relat:4,represent:5,request:2,requir:[2,4],respect:5,rest:2,right:2,routin:3,rpg:[3,4],rpg_helper:[1,2],run:[0,3,4],s:[0,3],sai:4,same:[3,5],save:3,scalar:[4,5],scan:[3,4],scan_endtime_to_tim:3,scan_quadr:4,scan_to_timeseri:3,scan_to_timeseries_from_dict:3,scan_transform:[1,2],scanflag:4,scanmod:4,scanob:4,scantime_from_aux:3,search:0,second:[3,4,5],see:4,seem:2,self:[3,4],sensor:4,seri:[3,4],set:3,set_coord:3,set_histori:2,set_statusflag:3,shape:4,sign:4,similar:5,singl:3,so:4,someth:2,sort:5,sourc:[2,3,4,5],specif:2,specifi:[2,3],spectra:[3,4],stabil:4,standard:2,star:4,start:3,station:[2,5],station_altitud:3,station_latitud:3,station_longitud:3,statu:4,statusflag:[3,4],step:4,store:[2,4],str:[4,5],stream:[2,4,5],string:[2,3,5],submodul:1,subpackag:1,suitabl:2,t:[3,4,5],t_diff:5,take:3,taken:3,tb:[3,4],temp:4,temperatur:[0,3,4],tempro:4,than:3,thi:[2,3,4],time:[2,3,4,5],time_end:[2,5],time_in:4,time_per_angl:3,time_raw:4,time_start:[2,5],time_vector:3,timecod:4,timedelta2:5,timedelta64:5,timeinputmiss:2,timeref:[],timereferror:2,timestamp:[3,4],to_dataset:3,too:[2,4],top:4,total:3,transform:[1,2,3,4],translat:4,tstab:4,tupl:4,two:4,type:[0,2,3,4],typic:2,under:2,uniqu:3,unknown:4,unknownfiletyp:2,unknownflagvalu:2,unpackbit:4,us:[2,3,4,5],usual:[2,5],utc:2,util:[1,2],v:0,valu:[2,3,4],variabl:[2,3,4],vars_opt:3,vector:[3,5],version:[2,4],via:4,wa:2,weather:4,welcom:0,when:[2,4],where:[2,4,5],which:[2,3,4],whole:4,wigo:5,wil:5,without:[3,5],work:4,wrapper:2,write:[0,2,4],write_from_dict:2,write_from_xarrai:2,write_netcdf:1,writer:2,wrong:2,wrongfiletyp:2,wronginputformat:2,wrongnumberofchannel:2,x:4,xarrai:[2,3,5],yaml:[2,5],yet:2,yyyymmdd:5,yyyymmddhhmm:5,yyyymmddhhmmss:5,zenith:3},titles:["mwr_raw2l1","mwr_raw2l1","mwr_raw2l1 package","mwr_raw2l1.measurement package","mwr_raw2l1.readers package","mwr_raw2l1.utils package"],titleterms:{base_reader_rpg:4,config_util:5,content:[0,2,3,4,5],error:2,file_util:5,indic:0,legacy_reader_rpg:4,log:2,main:2,measur:3,measurement_help:3,modul:[2,3,4,5],mwr_raw2l1:[0,1,2,3,4,5],packag:[2,3,4,5],reader:4,reader_radiometr:4,reader_rpg:4,reader_rpg_help:4,rpg_helper:3,scan_transform:3,submodul:[2,3,4,5],subpackag:2,tabl:0,transform:5,util:5,write_netcdf:2}})