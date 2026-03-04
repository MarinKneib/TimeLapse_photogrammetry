%% Initialize
clear
close all

cd('Z:\gl_kneibm\Projects\PI\2024_CAIRN-GLOBAL\TL_photogrammetry_Argentiere\data\TLCAM\Images\TLCAM_temp')

addpath('C:\Users\kneibm\Documents\UsefulCodes\Rename_files')
addpath('C:\Users\kneibm\Documents\UsefulCodes\ImGRAFT')

workingdir = 'Z:\gl_kneibm\Projects\PI\2024_CAIRN-GLOBAL\TL_photogrammetry_Argentiere\data\TLCAM\Images\TLCAM_temp\';
folders = dir([workingdir,'CAM*']);

destination_dir = 'Z:\gl_kneibm\Projects\PI\2024_CAIRN-GLOBAL\TL_photogrammetry_Argentiere\data\TLCAM\Images\';

for ff = 1:length(folders)
    folder = folders(ff).name;
    files = dir(fullfile(workingdir, folder, '**', '*.JPG'));
    % first deal with all files which have a wrong dates (date is
    % before october 2022): change date  
%     idx = [];
%     for cc = 1:length(files)
%         date = files(cc).date;
%         date = datetime(date,"InputFormat",'dd-MMM-yyyy HH:mm:ss',"Locale","fr_FR");
%         if date < datetime(2022,10,01)
%             idx = [idx cc];
%         end
%     end
%     dates2change = zeros(length(idx),4);
%     for cc = 1:length(idx)
%         YY = str2num(subfolder);
%         MM = str2num(files(cc).name(1:2));
%         DD = str2num(files(cc).name(3:4));
%         hh = 0;
%         dates2change(cc,:) = [YY,MM,DD,hh];
%     end
%     [~,~,count] = unique(dates2change(:, 1:3), 'rows');
%     dates2change(:,4) = count;
%     dates_changed = dates2change;
%     iii = 0;
%     for jj = 1:max(count)
%         iiii = 0;
%         for ii = 1:size(dates2change(dates2change(:,4)==jj,:),1)
%             iii=iii+1;
%             iiii = iiii+1;
%             dates_changed(iii,4) = 8+iiii;
%         end
%     end
%     for cc = 1:length(idx)
%         date = datetime(dates_changed(cc,1),dates_changed(cc,2),dates_changed(cc,3),dates_changed(cc,4),0,0,...
%             'Format','dd-MMM-yyyy HH:mm:ss','Locale','fr_FR');
%         date_str = string(date);
%         files(idx(cc)).date = date_str{:};
%     end


    % now move files
    for cc = 1:length(files)
        cc
        date = files(cc).date;
        date = strrep(date, 'Dec', 'déc.');
        date = strrep(date, 'Jan', 'janv');
        date = strrep(date, 'Feb', 'févr');
        date = string(datetime(date,"InputFormat",'dd-MMM-yyyy HH:mm:ss','Format','yyyy-MM-dd_HHmmss',"Locale","fr_FR"));
        camera = folder;
        new_file_name = [camera,'_',date{:},'.JPG'];
        movefile([files(cc).folder,'\',files(cc).name],[destination_dir,folder,'\',new_file_name]);
    end
end



