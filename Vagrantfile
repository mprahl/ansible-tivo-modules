# -*- mode: ruby -*-
# vi: set ft=ruby :

$script = <<SCRIPT
    dnf install -y \
        http://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm \
        http://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
    dnf install -y \
        ansible \
        python-requests \
        java \
        ffmpeg \
        autoconf \
        automake \
        libtool \
        argtable-devel \
        ffmpeg-devel \
        git-core
    mkdir /opt/tivo
    curl -L https://github.com/fflewddur/tivolibre/releases/download/v0.7.4/TivoDecoder.jar -o /opt/tivo/TivoDecoder.jar > /dev/null
    git clone git://github.com/erikkaashoek/Comskip --depth 1
    cd Comskip
    ./autogen.sh
    ./configure
    make
    mv comskip /opt/tivo/
    cd ~
    rm -rf Comskip
SCRIPT

Vagrant.configure(2) do |config|
    config.vm.box = "boxcutter/fedora25"
    config.vm.provider "libvirt" do |v, override|
        override.vm.box = "fedora/26-cloud-base"
    end
    config.vm.synced_folder "./", "/opt/ansible-tivo-modules"
    config.vm.provision "shell", inline: $script
    config.vm.provider "virtualbox" do |v|
        v.memory = 4096
        v.cpus = 4
    end
    config.vm.provider :libvirt do |v|
        v.memory = 4096
        v.cpus = 4
    end
end
